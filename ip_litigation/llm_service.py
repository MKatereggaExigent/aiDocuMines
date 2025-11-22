"""
LLM Service Layer for IP Litigation using DSPy.
Provides high-level services for patent analysis, infringement detection, and validity challenges.
"""

import dspy
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from .schemas import (
    PatentClassificationInput, PatentClassificationOutput,
    ClaimExtractionInput, ClaimExtractionOutput, ExtractedClaim,
    InfringementAnalysisInput, InfringementAnalysisOutput,
    ValidityChallengeInput, ValidityChallengeOutput,
    PatentDocumentType, ClaimType, InfringementType, ValidityChallengeType, LikelihoodLevel
)
from .dspy_signatures import (
    ClassifyPatentDocument, ExtractPatentClaims, AnalyzeInfringement,
    AnalyzeValidity, GenerateClaimChart, AnalyzePatentLandscape
)
from .models import PatentDocument, PatentClaim, InfringementAnalysis, ValidityChallenge


class PatentDocumentClassifier:
    """
    Service for classifying patent documents and extracting metadata.
    Uses DSPy to analyze patent documents and save results to the database.
    """
    
    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.classifier = dspy.ChainOfThought(ClassifyPatentDocument)
    
    def classify(self, input_data: PatentClassificationInput, analysis_run, user, client) -> PatentClassificationOutput:
        """
        Classify a patent document and save to database.
        
        Args:
            input_data: Patent classification input
            analysis_run: PatentAnalysisRun instance
            user: User performing the classification
            client: Client organization
            
        Returns:
            PatentClassificationOutput with classification results
        """
        # Run DSPy classification
        result = self.classifier(
            document_text=input_data.document_text,
            document_title=input_data.document_title or ""
        )
        
        # Parse IPC classes
        ipc_classes = [c.strip() for c in result.ipc_classes.split(',') if c.strip()]
        
        # Parse filing date
        filing_date = None
        if result.filing_date:
            try:
                filing_date = datetime.strptime(result.filing_date, '%Y-%m-%d').date()
            except:
                pass
        
        # Create output
        output = PatentClassificationOutput(
            document_type=PatentDocumentType(result.document_type),
            patent_number=result.patent_number if result.patent_number else None,
            application_number=result.application_number if result.application_number else None,
            filing_date=filing_date,
            title=result.title,
            abstract=result.abstract,
            technology_area=result.technology_area,
            ipc_classes=ipc_classes,
            confidence=float(result.confidence)
        )
        
        return output


class PatentClaimExtractor:
    """
    Service for extracting and analyzing patent claims.
    Uses DSPy to parse claims and save to the database.
    """
    
    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.extractor = dspy.ChainOfThought(ExtractPatentClaims)
    
    def extract_claims(self, input_data: ClaimExtractionInput, patent_document, user, client) -> ClaimExtractionOutput:
        """
        Extract claims from a patent document and save to database.
        
        Args:
            input_data: Claim extraction input
            patent_document: PatentDocument instance
            user: User performing the extraction
            client: Client organization
            
        Returns:
            ClaimExtractionOutput with extracted claims
        """
        # Run DSPy extraction
        result = self.extractor(
            patent_text=input_data.patent_text,
            patent_number=input_data.patent_number
        )
        
        # Parse claims JSON
        try:
            claims_data = json.loads(result.claims_json)
        except:
            claims_data = []
        
        # Create ExtractedClaim objects
        extracted_claims = []
        for claim_data in claims_data:
            claim = ExtractedClaim(
                claim_number=claim_data.get('claim_number', 0),
                claim_type=ClaimType(claim_data.get('claim_type', 'independent')),
                claim_text=claim_data.get('claim_text', ''),
                dependencies=claim_data.get('dependencies', []),
                key_limitations=claim_data.get('key_limitations', [])
            )
            extracted_claims.append(claim)
            
            # Save to database
            PatentClaim.objects.create(
                client=client,
                patent_document=patent_document,
                user=user,
                claim_number=claim.claim_number,
                claim_type=claim.claim_type.value,
                claim_text=claim.claim_text,
                dependencies=claim.dependencies,
                key_limitations=claim.key_limitations
            )
        
        # Create output
        output = ClaimExtractionOutput(
            claims=extracted_claims,
            total_claims=int(result.total_claims),
            independent_claims=int(result.independent_claims),
            dependent_claims=int(result.dependent_claims)
        )
        
        return output


class InfringementAnalyzer:
    """
    Service for analyzing patent infringement.
    Uses DSPy to compare patent claims against accused products.
    """
    
    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.analyzer = dspy.ChainOfThought(AnalyzeInfringement)
    
    def analyze(self, input_data: InfringementAnalysisInput, analysis_run, user, client) -> InfringementAnalysisOutput:
        """
        Analyze potential patent infringement and save to database.

        Args:
            input_data: Infringement analysis input
            analysis_run: PatentAnalysisRun instance
            user: User performing the analysis
            client: Client organization

        Returns:
            InfringementAnalysisOutput with analysis results
        """
        # Prepare claims text
        claims_text = '\n'.join(input_data.patent_claims)

        # Run DSPy analysis
        result = self.analyzer(
            patent_claims=claims_text,
            accused_product_description=input_data.accused_product_description,
            patent_number=input_data.patent_number
        )

        # Parse infringement types
        infringement_types = [InfringementType(t.strip()) for t in result.infringement_types.split(',') if t.strip()]

        # Parse claim-by-claim analysis
        try:
            claim_analysis = json.loads(result.claim_by_claim_analysis)
        except:
            claim_analysis = {}

        # Parse limitations
        limitations_met = [l.strip() for l in result.key_limitations_met.split(',') if l.strip()]
        limitations_not_met = [l.strip() for l in result.key_limitations_not_met.split(',') if l.strip()]

        # Create output
        output = InfringementAnalysisOutput(
            infringement_likelihood=LikelihoodLevel(result.infringement_likelihood),
            infringement_types=infringement_types,
            claim_by_claim_analysis=claim_analysis,
            key_limitations_met=limitations_met,
            key_limitations_not_met=limitations_not_met,
            equivalents_analysis=result.equivalents_analysis,
            recommendation=result.recommendation,
            confidence=float(result.confidence)
        )

        # Save to database
        InfringementAnalysis.objects.create(
            client=client,
            user=user,
            analysis_run=analysis_run,
            accused_product=input_data.accused_product_description[:500],
            infringement_type=infringement_types[0].value if infringement_types else 'literal',
            infringement_likelihood=output.infringement_likelihood.value,
            claim_by_claim_analysis=claim_analysis,
            key_findings=output.recommendation,
            equivalents_analysis=output.equivalents_analysis,
            recommendation=output.recommendation
        )

        return output


class ValidityChallengeAnalyzer:
    """
    Service for analyzing patent validity challenges.
    Uses DSPy to evaluate validity against prior art.
    """

    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.analyzer = dspy.ChainOfThought(AnalyzeValidity)

    def analyze(self, input_data: ValidityChallengeInput, analysis_run, user, client) -> ValidityChallengeOutput:
        """
        Analyze patent validity challenge and save to database.

        Args:
            input_data: Validity challenge input
            analysis_run: PatentAnalysisRun instance
            user: User performing the analysis
            client: Client organization

        Returns:
            ValidityChallengeOutput with analysis results
        """
        # Prepare input text
        claims_text = '\n'.join(input_data.patent_claims)
        prior_art_text = '\n'.join(input_data.prior_art_references)

        # Run DSPy analysis
        result = self.analyzer(
            patent_claims=claims_text,
            prior_art_references=prior_art_text,
            patent_number=input_data.patent_number,
            challenge_type=input_data.challenge_type.value
        )

        # Parse strongest prior art
        strongest_prior_art = [p.strip() for p in result.strongest_prior_art.split(',') if p.strip()]

        # Parse claim-by-claim analysis
        try:
            claim_analysis = json.loads(result.claim_by_claim_analysis)
        except:
            claim_analysis = {}

        # Parse key differences
        key_differences = [d.strip() for d in result.key_differences.split(',') if d.strip()]

        # Create output
        output = ValidityChallengeOutput(
            challenge_type=input_data.challenge_type,
            success_likelihood=LikelihoodLevel(result.success_likelihood),
            strongest_prior_art=strongest_prior_art,
            claim_by_claim_analysis=claim_analysis,
            key_differences=key_differences,
            obviousness_rationale=result.obviousness_rationale if result.obviousness_rationale else None,
            recommendation=result.recommendation,
            confidence=float(result.confidence)
        )

        # Save to database
        ValidityChallenge.objects.create(
            client=client,
            user=user,
            analysis_run=analysis_run,
            challenge_type=input_data.challenge_type.value,
            prior_art_references=strongest_prior_art,
            success_likelihood=output.success_likelihood.value,
            claim_by_claim_analysis=claim_analysis,
            key_arguments=key_differences,
            recommendation=output.recommendation
        )

        return output

