"""
Utility functions for regulatory compliance analysis.
"""
import re
import json
import logging
from typing import List, Dict, Any
from django.conf import settings
from django.utils import timezone
from core.models import File
from .models import ComplianceRun, RegulatoryRequirement

logger = logging.getLogger(__name__)


def extract_regulatory_requirements(document: File, framework: str) -> List[Dict[str, Any]]:
    """
    Extract regulatory requirements from framework documents.
    
    Args:
        document: File object containing regulatory framework document
        framework: Compliance framework type (gdpr, ccpa, etc.)
    
    Returns:
        List of requirement dictionaries
    """
    try:
        # Read document content
        with open(document.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        requirements = []
        
        if framework == 'gdpr':
            requirements = _extract_gdpr_requirements(content)
        elif framework == 'ccpa':
            requirements = _extract_ccpa_requirements(content)
        elif framework == 'hipaa':
            requirements = _extract_hipaa_requirements(content)
        elif framework == 'sox':
            requirements = _extract_sox_requirements(content)
        else:
            requirements = _extract_generic_requirements(content)
        
        logger.info(f"Extracted {len(requirements)} requirements from {document.filename}")
        return requirements
        
    except Exception as e:
        logger.error(f"Error extracting requirements from {document.filename}: {str(e)}")
        return []


def _extract_gdpr_requirements(content: str) -> List[Dict[str, Any]]:
    """Extract GDPR-specific requirements."""
    requirements = []
    
    # GDPR article patterns
    article_pattern = r'Article\s+(\d+)\s*[-–]\s*([^\n]+)'
    articles = re.findall(article_pattern, content, re.IGNORECASE)
    
    for article_num, title in articles:
        # Extract article content
        article_content_pattern = rf'Article\s+{article_num}\s*[-–]\s*{re.escape(title)}(.*?)(?=Article\s+\d+|$)'
        article_match = re.search(article_content_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if article_match:
            article_text = article_match.group(1).strip()
            
            # Categorize based on article number
            category = _categorize_gdpr_article(int(article_num))
            risk_level = _assess_gdpr_risk_level(int(article_num))
            
            requirements.append({
                'requirement_id': f'GDPR-ART-{article_num}',
                'title': title.strip(),
                'text': article_text[:2000],  # Limit text length
                'category': category,
                'risk_level': risk_level
            })
    
    return requirements


def _extract_ccpa_requirements(content: str) -> List[Dict[str, Any]]:
    """Extract CCPA-specific requirements."""
    requirements = []
    
    # CCPA section patterns
    section_pattern = r'Section\s+(\d+)\s*\.?\s*([^\n]+)'
    sections = re.findall(section_pattern, content, re.IGNORECASE)
    
    for section_num, title in sections:
        section_content_pattern = rf'Section\s+{section_num}\s*\.?\s*{re.escape(title)}(.*?)(?=Section\s+\d+|$)'
        section_match = re.search(section_content_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if section_match:
            section_text = section_match.group(1).strip()
            
            category = _categorize_ccpa_section(int(section_num))
            risk_level = _assess_ccpa_risk_level(int(section_num))
            
            requirements.append({
                'requirement_id': f'CCPA-SEC-{section_num}',
                'title': title.strip(),
                'text': section_text[:2000],
                'category': category,
                'risk_level': risk_level
            })
    
    return requirements


def _extract_hipaa_requirements(content: str) -> List[Dict[str, Any]]:
    """Extract HIPAA-specific requirements."""
    requirements = []
    
    # HIPAA rule patterns
    rule_pattern = r'§\s*(\d+\.\d+)\s+([^\n]+)'
    rules = re.findall(rule_pattern, content, re.IGNORECASE)
    
    for rule_num, title in rules:
        rule_content_pattern = rf'§\s*{re.escape(rule_num)}\s+{re.escape(title)}(.*?)(?=§\s*\d+\.\d+|$)'
        rule_match = re.search(rule_content_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if rule_match:
            rule_text = rule_match.group(1).strip()
            
            category = _categorize_hipaa_rule(rule_num)
            risk_level = _assess_hipaa_risk_level(rule_num)
            
            requirements.append({
                'requirement_id': f'HIPAA-{rule_num}',
                'title': title.strip(),
                'text': rule_text[:2000],
                'category': category,
                'risk_level': risk_level
            })
    
    return requirements


def _extract_sox_requirements(content: str) -> List[Dict[str, Any]]:
    """Extract SOX-specific requirements."""
    requirements = []
    
    # SOX section patterns
    section_pattern = r'Section\s+(\d+)\s*([^\n]+)'
    sections = re.findall(section_pattern, content, re.IGNORECASE)
    
    for section_num, title in sections:
        section_content_pattern = rf'Section\s+{section_num}\s+{re.escape(title)}(.*?)(?=Section\s+\d+|$)'
        section_match = re.search(section_content_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if section_match:
            section_text = section_match.group(1).strip()
            
            category = _categorize_sox_section(int(section_num))
            risk_level = _assess_sox_risk_level(int(section_num))
            
            requirements.append({
                'requirement_id': f'SOX-SEC-{section_num}',
                'title': title.strip(),
                'text': section_text[:2000],
                'category': category,
                'risk_level': risk_level
            })
    
    return requirements


def _extract_generic_requirements(content: str) -> List[Dict[str, Any]]:
    """Extract requirements from generic compliance documents."""
    requirements = []
    
    # Generic requirement patterns
    patterns = [
        r'Requirement\s+(\d+)\s*[-:]\s*([^\n]+)',
        r'Control\s+(\d+)\s*[-:]\s*([^\n]+)',
        r'Standard\s+(\d+)\s*[-:]\s*([^\n]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for req_num, title in matches:
            requirements.append({
                'requirement_id': f'REQ-{req_num}',
                'title': title.strip(),
                'text': title.strip(),
                'category': 'other',
                'risk_level': 'medium'
            })
    
    return requirements


def _categorize_gdpr_article(article_num: int) -> str:
    """Categorize GDPR articles by type."""
    if article_num in [5, 6, 7, 8, 9]:
        return 'data_protection'
    elif article_num in [12, 13, 14]:
        return 'privacy_rights'
    elif article_num in [32, 33, 34]:
        return 'security_controls'
    elif article_num in [33, 34]:
        return 'breach_notification'
    elif article_num in [7, 8]:
        return 'consent_management'
    elif article_num in [17, 18]:
        return 'data_retention'
    elif article_num in [44, 45, 46]:
        return 'cross_border_transfer'
    else:
        return 'other'


def _assess_gdpr_risk_level(article_num: int) -> str:
    """Assess risk level for GDPR articles."""
    critical_articles = [5, 6, 32, 33, 34]  # Core data protection, security, breach
    high_articles = [7, 8, 9, 17, 18, 44, 45, 46]  # Consent, retention, transfers
    
    if article_num in critical_articles:
        return 'critical'
    elif article_num in high_articles:
        return 'high'
    else:
        return 'medium'


def _categorize_ccpa_section(section_num: int) -> str:
    """Categorize CCPA sections by type."""
    if section_num in [1798.100, 1798.105, 1798.110]:
        return 'privacy_rights'
    elif section_num in [1798.120, 1798.125]:
        return 'consent_management'
    elif section_num in [1798.130, 1798.135]:
        return 'data_protection'
    elif section_num in [1798.140, 1798.145]:
        return 'vendor_management'
    else:
        return 'other'


def _assess_ccpa_risk_level(section_num: int) -> str:
    """Assess risk level for CCPA sections."""
    critical_sections = [1798.100, 1798.105, 1798.110, 1798.120]
    high_sections = [1798.125, 1798.130, 1798.135]
    
    if section_num in critical_sections:
        return 'critical'
    elif section_num in high_sections:
        return 'high'
    else:
        return 'medium'


def _categorize_hipaa_rule(rule_num: str) -> str:
    """Categorize HIPAA rules by type."""
    if rule_num.startswith('164.3'):
        return 'security_controls'
    elif rule_num.startswith('164.4'):
        return 'breach_notification'
    elif rule_num.startswith('164.5'):
        return 'data_protection'
    else:
        return 'other'


def _assess_hipaa_risk_level(rule_num: str) -> str:
    """Assess risk level for HIPAA rules."""
    critical_rules = ['164.306', '164.308', '164.312', '164.404']
    high_rules = ['164.310', '164.314', '164.316', '164.408']
    
    if rule_num in critical_rules:
        return 'critical'
    elif rule_num in high_rules:
        return 'high'
    else:
        return 'medium'


def _categorize_sox_section(section_num: int) -> str:
    """Categorize SOX sections by type."""
    if section_num in [302, 404, 906]:
        return 'audit_logging'
    elif section_num in [301, 407]:
        return 'security_controls'
    else:
        return 'other'


def _assess_sox_risk_level(section_num: int) -> str:
    """Assess risk level for SOX sections."""
    critical_sections = [302, 404, 906]
    high_sections = [301, 407]
    
    if section_num in critical_sections:
        return 'critical'
    elif section_num in high_sections:
        return 'high'
    else:
        return 'medium'


def analyze_policy_compliance(policy_document: File, requirements: List[RegulatoryRequirement], framework: str) -> Dict[str, Any]:
    """
    Analyze policy document compliance against regulatory requirements.
    
    Args:
        policy_document: Policy document to analyze
        requirements: List of regulatory requirements
        framework: Compliance framework
    
    Returns:
        Dictionary containing policy analysis results
    """
    try:
        # Read policy document content
        with open(policy_document.file_path, 'r', encoding='utf-8') as f:
            policy_content = f.read()
        
        mappings = []
        
        for requirement in requirements:
            # Analyze mapping between policy and requirement
            mapping_result = _analyze_requirement_mapping(
                policy_content,
                requirement,
                policy_document.filename
            )
            
            if mapping_result['mapping_strength'] != 'none':
                mappings.append({
                    'requirement_id': requirement.id,
                    'policy_name': policy_document.filename,
                    'policy_section': mapping_result.get('policy_section', ''),
                    'mapping_strength': mapping_result['mapping_strength'],
                    'gap_analysis': mapping_result.get('gap_analysis', ''),
                    'recommendations': mapping_result.get('recommendations', []),
                    'confidence': mapping_result.get('confidence', 0.0)
                })
        
        return {
            'policy_document': policy_document.filename,
            'mappings': mappings,
            'total_mappings': len(mappings),
            'framework': framework
        }
        
    except Exception as e:
        logger.error(f"Error analyzing policy compliance for {policy_document.filename}: {str(e)}")
        return {'policy_document': policy_document.filename, 'mappings': [], 'error': str(e)}


def _analyze_requirement_mapping(policy_content: str, requirement: RegulatoryRequirement, policy_name: str) -> Dict[str, Any]:
    """Analyze mapping between policy content and regulatory requirement."""
    
    # Extract key terms from requirement
    requirement_terms = _extract_key_terms(requirement.requirement_text)
    
    # Search for requirement terms in policy content
    matches = []
    for term in requirement_terms:
        if term.lower() in policy_content.lower():
            matches.append(term)
    
    # Calculate mapping strength based on term matches
    match_ratio = len(matches) / len(requirement_terms) if requirement_terms else 0
    
    if match_ratio >= 0.8:
        mapping_strength = 'strong'
        confidence = 0.9
    elif match_ratio >= 0.5:
        mapping_strength = 'moderate'
        confidence = 0.7
    elif match_ratio >= 0.2:
        mapping_strength = 'weak'
        confidence = 0.4
    else:
        mapping_strength = 'none'
        confidence = 0.1
    
    # Generate gap analysis and recommendations
    gap_analysis = ""
    recommendations = []
    
    if mapping_strength in ['weak', 'moderate']:
        missing_terms = [term for term in requirement_terms if term.lower() not in policy_content.lower()]
        gap_analysis = f"Policy may not fully address: {', '.join(missing_terms[:5])}"
        recommendations = [
            f"Consider adding explicit language about {term}" for term in missing_terms[:3]
        ]
    
    return {
        'mapping_strength': mapping_strength,
        'confidence': confidence,
        'gap_analysis': gap_analysis,
        'recommendations': recommendations,
        'matched_terms': matches
    }


def _extract_key_terms(text: str) -> List[str]:
    """Extract key terms from requirement text."""
    # Common compliance terms
    key_terms = [
        'personal data', 'data subject', 'consent', 'processing', 'controller',
        'processor', 'breach', 'notification', 'security', 'encryption',
        'access control', 'audit', 'retention', 'deletion', 'privacy',
        'confidentiality', 'integrity', 'availability', 'risk assessment',
        'data protection', 'compliance', 'monitoring', 'training'
    ]
    
    # Find key terms in the text
    found_terms = []
    text_lower = text.lower()
    
    for term in key_terms:
        if term in text_lower:
            found_terms.append(term)
    
    # Also extract capitalized terms (likely important concepts)
    capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    capitalized_terms = re.findall(capitalized_pattern, text)
    
    # Combine and deduplicate
    all_terms = list(set(found_terms + [term.lower() for term in capitalized_terms]))
    
    return all_terms[:20]  # Limit to top 20 terms


def search_personal_data(data_source: str, email: str, name: str, subject_id: str = None) -> Dict[str, Any]:
    """
    Search for personal data in various data sources.

    Args:
        data_source: Data source to search (database, files, etc.)
        email: Data subject email
        name: Data subject name
        subject_id: Optional internal ID for data subject

    Returns:
        Dictionary containing search results
    """
    try:
        # This is a mock implementation - in practice, this would integrate
        # with actual data sources like databases, file systems, etc.

        search_results = {
            'data_source': data_source,
            'data_found': False,
            'records_found': 0,
            'data_categories': [],
            'search_terms': [email, name]
        }

        if subject_id:
            search_results['search_terms'].append(subject_id)

        # Mock search logic based on data source
        if data_source == 'user_database':
            # Simulate database search
            search_results.update({
                'data_found': True,
                'records_found': 5,
                'data_categories': ['contact_info', 'account_data', 'preferences']
            })
        elif data_source == 'document_storage':
            # Simulate document search
            search_results.update({
                'data_found': True,
                'records_found': 12,
                'data_categories': ['documents', 'metadata', 'access_logs']
            })
        elif data_source == 'email_systems':
            # Simulate email search
            search_results.update({
                'data_found': True,
                'records_found': 8,
                'data_categories': ['email_content', 'email_metadata']
            })
        elif data_source == 'backup_systems':
            # Simulate backup search
            search_results.update({
                'data_found': False,
                'records_found': 0,
                'data_categories': []
            })
        elif data_source == 'log_files':
            # Simulate log search
            search_results.update({
                'data_found': True,
                'records_found': 25,
                'data_categories': ['access_logs', 'activity_logs']
            })

        logger.info(f"Searched {data_source} for {email}: {search_results['records_found']} records found")
        return search_results

    except Exception as e:
        logger.error(f"Error searching {data_source} for personal data: {str(e)}")
        return {
            'data_source': data_source,
            'data_found': False,
            'records_found': 0,
            'data_categories': [],
            'error': str(e)
        }


def redact_document_content(document: File, redaction_type: str, redaction_rules: List[Dict], redaction_patterns: List[str]) -> Dict[str, Any]:
    """
    Redact sensitive content from documents.

    Args:
        document: Document to redact
        redaction_type: Type of redaction (pii, phi, etc.)
        redaction_rules: List of redaction rules
        redaction_patterns: List of regex patterns for redaction

    Returns:
        Dictionary containing redaction results
    """
    try:
        # Read document content
        with open(document.file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        redaction_count = 0
        redaction_summary = {}

        # Apply predefined patterns based on redaction type
        if redaction_type == 'pii':
            patterns = _get_pii_patterns()
        elif redaction_type == 'phi':
            patterns = _get_phi_patterns()
        elif redaction_type == 'financial':
            patterns = _get_financial_patterns()
        else:
            patterns = []

        # Add custom patterns
        patterns.extend(redaction_patterns)

        # Apply redaction patterns
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                redaction_count += len(matches)
                pattern_name = _get_pattern_name(pattern)
                redaction_summary[pattern_name] = len(matches)

                # Replace matches with redaction marker
                content = re.sub(pattern, '[REDACTED]', content, flags=re.IGNORECASE)

        # Apply custom redaction rules
        for rule in redaction_rules:
            rule_pattern = rule.get('pattern', '')
            replacement = rule.get('replacement', '[REDACTED]')

            if rule_pattern:
                matches = re.findall(rule_pattern, content, re.IGNORECASE)
                if matches:
                    redaction_count += len(matches)
                    rule_name = rule.get('name', 'custom_rule')
                    redaction_summary[rule_name] = len(matches)

                    content = re.sub(rule_pattern, replacement, content, flags=re.IGNORECASE)

        # Save redacted content to new file
        redacted_file_path = document.file_path.replace('.', '_redacted.')
        with open(redacted_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Calculate file size
        import os
        redacted_file_size = os.path.getsize(redacted_file_path)

        return {
            'success': True,
            'redaction_count': redaction_count,
            'redaction_summary': redaction_summary,
            'redacted_file_path': redacted_file_path,
            'redacted_file_size': redacted_file_size,
            'processing_metadata': {
                'original_length': len(original_content),
                'redacted_length': len(content),
                'patterns_applied': len(patterns) + len(redaction_rules)
            }
        }

    except Exception as e:
        logger.error(f"Error redacting document {document.filename}: {str(e)}")
        return {
            'success': False,
            'redaction_count': 0,
            'redaction_summary': {},
            'error': str(e)
        }


def _get_pii_patterns() -> List[str]:
    """Get regex patterns for PII redaction."""
    return [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card numbers
        r'\b\d{1,2}\/\d{1,2}\/\d{4}\b',  # Dates
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Names (simple pattern)
    ]


def _get_phi_patterns() -> List[str]:
    """Get regex patterns for PHI redaction."""
    return [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\bMRN:?\s*\d+\b',  # Medical record numbers
        r'\bDOB:?\s*\d{1,2}\/\d{1,2}\/\d{4}\b',  # Date of birth
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Names
    ]


def _get_financial_patterns() -> List[str]:
    """Get regex patterns for financial information redaction."""
    return [
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card numbers
        r'\b\d{9,18}\b',  # Bank account numbers
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\$\d+(?:,\d{3})*(?:\.\d{2})?\b',  # Dollar amounts
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',  # IBAN
    ]


def _get_pattern_name(pattern: str) -> str:
    """Get a human-readable name for a regex pattern."""
    pattern_names = {
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': 'email_addresses',
        r'\b\d{3}-\d{2}-\d{4}\b': 'ssn',
        r'\b\d{3}-\d{3}-\d{4}\b': 'phone_numbers',
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b': 'credit_cards',
        r'\b\d{1,2}\/\d{1,2}\/\d{4}\b': 'dates',
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b': 'names',
    }

    return pattern_names.get(pattern, 'custom_pattern')


def generate_compliance_report(compliance_run: ComplianceRun, report_type: str, include_sections: List[str]) -> Dict[str, Any]:
    """
    Generate comprehensive compliance reports.

    Args:
        compliance_run: ComplianceRun instance
        report_type: Type of report to generate
        include_sections: Sections to include in report

    Returns:
        Dictionary containing report generation results
    """
    try:
        # This is a mock implementation - in practice, this would generate
        # actual PDF reports using libraries like ReportLab or WeasyPrint

        report_content = _generate_report_content(compliance_run, report_type, include_sections)

        # Mock file creation
        import tempfile
        import os

        # Create temporary file for the report
        temp_dir = tempfile.gettempdir()
        report_filename = f"compliance_report_{compliance_run.id}_{report_type}.pdf"
        report_file_path = os.path.join(temp_dir, report_filename)

        # Write mock PDF content (in practice, this would be actual PDF generation)
        with open(report_file_path, 'w') as f:
            f.write(report_content)

        report_file_size = os.path.getsize(report_file_path)

        return {
            'success': True,
            'report_file_path': report_file_path,
            'report_file_size': report_file_size,
            'metadata': {
                'report_type': report_type,
                'sections_included': include_sections,
                'compliance_framework': compliance_run.compliance_framework,
                'organization': compliance_run.organization_name,
                'generated_at': timezone.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error generating compliance report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def _generate_report_content(compliance_run: ComplianceRun, report_type: str, include_sections: List[str]) -> str:
    """Generate report content based on type and sections."""

    content = f"""
    COMPLIANCE REPORT

    Organization: {compliance_run.organization_name}
    Framework: {compliance_run.get_compliance_framework_display()}
    Assessment Period: {compliance_run.assessment_start_date} to {compliance_run.assessment_end_date}
    Report Type: {report_type.replace('_', ' ').title()}

    """

    if 'executive_summary' in include_sections:
        content += """
    EXECUTIVE SUMMARY

    This report provides an assessment of regulatory compliance for the specified framework.
    Key findings and recommendations are outlined in the following sections.

    """

    if 'requirements_analysis' in include_sections:
        content += """
    REQUIREMENTS ANALYSIS

    Analysis of regulatory requirements and current compliance status.

    """

    if 'gap_analysis' in include_sections:
        content += """
    GAP ANALYSIS

    Identification of compliance gaps and areas requiring attention.

    """

    if 'remediation_plan' in include_sections:
        content += """
    REMEDIATION PLAN

    Recommended actions to address compliance gaps and improve overall compliance posture.

    """

    return content
