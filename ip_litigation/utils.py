"""
Utility functions for the IP Litigation application.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from .models import (
    PatentAnalysisRun, PatentDocument, PatentClaim, PriorArtDocument,
    ClaimChart, InfringementAnalysis, ValidityChallenge
)

logger = logging.getLogger(__name__)
User = get_user_model()


def parse_patent_number(patent_number: str) -> Dict:
    """
    Parse patent number to extract country, number, and kind code.
    """
    patent_info = {
        'country': '',
        'number': '',
        'kind_code': '',
        'formatted': patent_number.strip().upper()
    }
    
    # Remove spaces and convert to uppercase
    clean_number = patent_number.replace(' ', '').upper()
    
    # US Patent patterns
    us_patterns = [
        r'^US(\d{7,8})([A-Z]\d?)$',  # US1234567B2
        r'^(\d{7,8})$',              # 1234567 (assume US)
        r'^US(\d{4}/\d{6})$'         # US2020/123456 (application)
    ]
    
    for pattern in us_patterns:
        match = re.match(pattern, clean_number)
        if match:
            patent_info['country'] = 'US'
            if len(match.groups()) == 2:
                patent_info['number'] = match.group(1)
                patent_info['kind_code'] = match.group(2)
            else:
                patent_info['number'] = match.group(1)
            break
    
    # European Patent patterns
    ep_patterns = [
        r'^EP(\d{7})([A-Z]\d?)$',    # EP1234567A1
        r'^EP(\d{4}/\d{6})$'         # EP2020/123456 (application)
    ]
    
    for pattern in ep_patterns:
        match = re.match(pattern, clean_number)
        if match:
            patent_info['country'] = 'EP'
            patent_info['number'] = match.group(1)
            if len(match.groups()) == 2:
                patent_info['kind_code'] = match.group(2)
            break
    
    return patent_info


def extract_patent_claims(patent_text: str) -> List[Dict]:
    """
    Extract patent claims from patent document text.
    """
    claims = []
    
    # Look for claims section
    claims_section_patterns = [
        r'CLAIMS?\s*\n(.*?)(?=\n\s*(?:ABSTRACT|BRIEF DESCRIPTION|DETAILED DESCRIPTION|$))',
        r'What is claimed is:\s*\n(.*?)(?=\n\s*(?:ABSTRACT|BRIEF DESCRIPTION|DETAILED DESCRIPTION|$))',
        r'I claim:\s*\n(.*?)(?=\n\s*(?:ABSTRACT|BRIEF DESCRIPTION|DETAILED DESCRIPTION|$))'
    ]
    
    claims_text = ""
    for pattern in claims_section_patterns:
        match = re.search(pattern, patent_text, re.DOTALL | re.IGNORECASE)
        if match:
            claims_text = match.group(1)
            break
    
    if not claims_text:
        return claims
    
    # Split into individual claims
    claim_pattern = r'(\d+)\.\s*(.*?)(?=\n\s*\d+\.|$)'
    claim_matches = re.findall(claim_pattern, claims_text, re.DOTALL)
    
    for claim_num, claim_text in claim_matches:
        claim_text = claim_text.strip()
        
        # Determine claim type
        claim_type = 'independent'
        depends_on = []
        
        # Check for dependency
        dependency_patterns = [
            r'The\s+(?:method|apparatus|system|device)\s+of\s+claim\s+(\d+)',
            r'The\s+(?:method|apparatus|system|device)\s+according\s+to\s+claim\s+(\d+)',
            r'A\s+(?:method|apparatus|system|device)\s+as\s+claimed\s+in\s+claim\s+(\d+)'
        ]
        
        for pattern in dependency_patterns:
            matches = re.findall(pattern, claim_text, re.IGNORECASE)
            if matches:
                claim_type = 'dependent'
                depends_on = [int(m) for m in matches]
                break
        
        # Extract claim elements
        elements = extract_claim_elements(claim_text)
        
        claims.append({
            'claim_number': int(claim_num),
            'claim_text': claim_text,
            'claim_type': claim_type,
            'depends_on_claims': depends_on,
            'claim_elements': elements,
            'element_count': len(elements)
        })
    
    return claims


def extract_claim_elements(claim_text: str) -> List[str]:
    """
    Extract individual elements/limitations from a patent claim.
    """
    elements = []
    
    # Remove claim preamble and transitional phrase
    # Look for common transitional phrases
    transitional_phrases = [
        r'comprising:?\s*',
        r'including:?\s*',
        r'having:?\s*',
        r'wherein:?\s*',
        r'characterized by:?\s*'
    ]
    
    working_text = claim_text
    for phrase in transitional_phrases:
        working_text = re.sub(phrase, '|||TRANSITION|||', working_text, flags=re.IGNORECASE)
    
    # Split on transition and take the part after
    parts = working_text.split('|||TRANSITION|||')
    if len(parts) > 1:
        elements_text = parts[1]
    else:
        elements_text = working_text
    
    # Split on common element separators
    element_separators = [
        r';\s*(?:and\s+)?',  # semicolon with optional "and"
        r',\s*(?:and\s+)?',  # comma with optional "and"
        r'\s+and\s+',        # standalone "and"
        r'\s+wherein\s+',    # "wherein" clauses
        r'\s+such\s+that\s+' # "such that" clauses
    ]
    
    current_elements = [elements_text.strip()]
    
    for separator in element_separators:
        new_elements = []
        for element in current_elements:
            split_elements = re.split(separator, element, flags=re.IGNORECASE)
            new_elements.extend([e.strip() for e in split_elements if e.strip()])
        current_elements = new_elements
    
    # Clean up elements
    for element in current_elements:
        if len(element) > 10:  # Filter out very short fragments
            # Remove leading/trailing punctuation
            clean_element = re.sub(r'^[^\w]*|[^\w]*$', '', element)
            if clean_element:
                elements.append(clean_element)
    
    return elements


def calculate_claim_complexity(claim_elements: List[str]) -> float:
    """
    Calculate complexity score for a patent claim based on its elements.
    """
    if not claim_elements:
        return 0.0
    
    # Base complexity from number of elements
    element_count_score = min(1.0, len(claim_elements) / 10.0)
    
    # Complexity from element content
    complexity_indicators = [
        'wherein', 'such that', 'characterized by', 'further comprising',
        'optionally', 'preferably', 'alternatively', 'specifically'
    ]
    
    complexity_bonus = 0.0
    total_words = 0
    
    for element in claim_elements:
        element_lower = element.lower()
        total_words += len(element.split())
        
        # Check for complexity indicators
        for indicator in complexity_indicators:
            if indicator in element_lower:
                complexity_bonus += 0.1
    
    # Average words per element
    avg_words_per_element = total_words / len(claim_elements) if claim_elements else 0
    word_complexity = min(0.3, avg_words_per_element / 20.0)
    
    # Final complexity score
    complexity_score = element_count_score + word_complexity + min(0.3, complexity_bonus)
    
    return min(1.0, complexity_score)


def analyze_patent_landscape(analysis_run: PatentAnalysisRun) -> Dict:
    """
    Analyze patent landscape for technology area.
    """
    patents = PatentDocument.objects.filter(analysis_run=analysis_run)
    
    if not patents.exists():
        return {"error": "No patents found for analysis"}
    
    # Analyze patent offices
    office_distribution = {}
    for office_choice in PatentDocument._meta.get_field('patent_office').choices:
        office_code, office_name = office_choice
        count = patents.filter(patent_office=office_code).count()
        if count > 0:
            office_distribution[office_name] = count
    
    # Analyze assignees
    assignee_counts = {}
    for patent in patents:
        for assignee in patent.assignees:
            assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    # Top assignees
    top_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Analyze filing trends by year
    filing_trends = {}
    for patent in patents:
        if patent.filing_date:
            year = patent.filing_date.year
            filing_trends[year] = filing_trends.get(year, 0) + 1
    
    # Classification analysis
    ipc_classes = {}
    cpc_classes = {}
    
    for patent in patents:
        for ipc in patent.ipc_classes:
            ipc_classes[ipc] = ipc_classes.get(ipc, 0) + 1
        for cpc in patent.cpc_classes:
            cpc_classes[cpc] = cpc_classes.get(cpc, 0) + 1
    
    return {
        'total_patents': patents.count(),
        'office_distribution': office_distribution,
        'top_assignees': top_assignees,
        'filing_trends': dict(sorted(filing_trends.items())),
        'top_ipc_classes': sorted(ipc_classes.items(), key=lambda x: x[1], reverse=True)[:10],
        'top_cpc_classes': sorted(cpc_classes.items(), key=lambda x: x[1], reverse=True)[:10],
        'analysis_period': {
            'start': analysis_run.created_at.isoformat(),
            'technology_area': analysis_run.technology_area
        }
    }


def generate_infringement_report(analysis_run: PatentAnalysisRun) -> Dict:
    """
    Generate comprehensive infringement analysis report.
    """
    analyses = InfringementAnalysis.objects.filter(analysis_run=analysis_run)
    
    if not analyses.exists():
        return {"error": "No infringement analyses found"}
    
    # Aggregate statistics
    total_analyses = analyses.count()
    infringement_found = analyses.filter(infringement_conclusion='infringes').count()
    no_infringement = analyses.filter(infringement_conclusion='does_not_infringe').count()
    mixed_results = analyses.filter(infringement_conclusion='mixed').count()
    inconclusive = analyses.filter(infringement_conclusion='inconclusive').count()
    
    # Confidence analysis
    high_confidence = analyses.filter(confidence_level='high').count()
    medium_confidence = analyses.filter(confidence_level='medium').count()
    low_confidence = analyses.filter(confidence_level='low').count()
    
    # Literal vs DOE analysis
    literal_infringement = analyses.filter(literal_infringement='yes').count()
    doe_infringement = analyses.filter(doctrine_of_equivalents='yes').count()
    
    # Risk assessment
    high_risk_products = []
    for analysis in analyses.filter(infringement_conclusion='infringes', confidence_level='high'):
        high_risk_products.append({
            'product': analysis.accused_product,
            'analysis_name': analysis.analysis_name,
            'patents_count': analysis.asserted_patents.count()
        })
    
    return {
        'summary': {
            'total_analyses': total_analyses,
            'infringement_rate': (infringement_found / total_analyses * 100) if total_analyses > 0 else 0,
            'high_confidence_rate': (high_confidence / total_analyses * 100) if total_analyses > 0 else 0
        },
        'conclusion_breakdown': {
            'infringes': infringement_found,
            'does_not_infringe': no_infringement,
            'mixed_results': mixed_results,
            'inconclusive': inconclusive
        },
        'confidence_breakdown': {
            'high': high_confidence,
            'medium': medium_confidence,
            'low': low_confidence
        },
        'infringement_type': {
            'literal_infringement': literal_infringement,
            'doctrine_of_equivalents': doe_infringement
        },
        'high_risk_products': high_risk_products,
        'recommendations': generate_infringement_recommendations(analyses)
    }


def generate_infringement_recommendations(analyses) -> List[str]:
    """
    Generate recommendations based on infringement analysis results.
    """
    recommendations = []
    
    total_analyses = analyses.count()
    infringement_found = analyses.filter(infringement_conclusion='infringes').count()
    high_confidence_infringement = analyses.filter(
        infringement_conclusion='infringes',
        confidence_level='high'
    ).count()
    
    if high_confidence_infringement > 0:
        recommendations.append(f"Immediate attention required: {high_confidence_infringement} high-confidence infringement findings")
        recommendations.append("Consider design-around strategies for infringing products")
        recommendations.append("Evaluate patent validity challenges as potential defense")
    
    if infringement_found > total_analyses * 0.5:
        recommendations.append("High infringement risk across product portfolio")
        recommendations.append("Consider comprehensive IP clearance review")
    
    inconclusive_count = analyses.filter(infringement_conclusion='inconclusive').count()
    if inconclusive_count > 0:
        recommendations.append(f"Obtain expert technical analysis for {inconclusive_count} inconclusive cases")
    
    return recommendations


def calculate_validity_challenge_strength(challenge: ValidityChallenge) -> Dict:
    """
    Calculate the strength of a patent validity challenge.
    """
    prior_art_refs = challenge.prior_art_references.all()
    
    if not prior_art_refs.exists():
        return {"strength": "weak", "score": 0.0, "factors": []}
    
    strength_factors = []
    total_score = 0.0
    
    # Analyze prior art quality
    high_relevance_count = prior_art_refs.filter(relevance_score__gte=0.8).count()
    medium_relevance_count = prior_art_refs.filter(relevance_score__gte=0.5, relevance_score__lt=0.8).count()
    
    if high_relevance_count > 0:
        total_score += high_relevance_count * 0.3
        strength_factors.append(f"{high_relevance_count} high-relevance prior art references")
    
    if medium_relevance_count > 0:
        total_score += medium_relevance_count * 0.15
        strength_factors.append(f"{medium_relevance_count} medium-relevance prior art references")
    
    # Analyze prior art types
    patent_refs = prior_art_refs.filter(document_type='patent').count()
    publication_refs = prior_art_refs.filter(document_type='publication').count()
    
    if patent_refs >= 2:
        total_score += 0.2
        strength_factors.append("Multiple patent references available")
    
    if publication_refs >= 1:
        total_score += 0.1
        strength_factors.append("Scientific publication references available")
    
    # Analyze challenge grounds
    if 'anticipation' in challenge.challenge_grounds and 'obviousness' in challenge.challenge_grounds:
        total_score += 0.2
        strength_factors.append("Both anticipation and obviousness grounds available")
    
    # Determine overall strength
    if total_score >= 0.7:
        strength = "strong"
    elif total_score >= 0.4:
        strength = "moderate"
    else:
        strength = "weak"
    
    return {
        "strength": strength,
        "score": min(1.0, total_score),
        "factors": strength_factors,
        "prior_art_count": prior_art_refs.count()
    }
