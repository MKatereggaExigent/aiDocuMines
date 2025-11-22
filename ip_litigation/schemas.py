"""
Pydantic schemas for IP Litigation LLM processing.
Provides type-safe data validation for patent analysis, infringement detection, and validity challenges.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date


# ============================================================================
# ENUMS
# ============================================================================

class PatentDocumentType(str, Enum):
    """Types of patent documents"""
    UTILITY_PATENT = "utility_patent"
    DESIGN_PATENT = "design_patent"
    PLANT_PATENT = "plant_patent"
    PROVISIONAL_APPLICATION = "provisional_application"
    PCT_APPLICATION = "pct_application"
    CONTINUATION = "continuation"
    DIVISIONAL = "divisional"
    REISSUE = "reissue"


class ClaimType(str, Enum):
    """Types of patent claims"""
    INDEPENDENT = "independent"
    DEPENDENT = "dependent"
    METHOD = "method"
    APPARATUS = "apparatus"
    COMPOSITION = "composition"
    SYSTEM = "system"


class InfringementType(str, Enum):
    """Types of patent infringement"""
    LITERAL = "literal"
    DOCTRINE_OF_EQUIVALENTS = "doctrine_of_equivalents"
    INDIRECT = "indirect"
    CONTRIBUTORY = "contributory"
    INDUCED = "induced"
    WILLFUL = "willful"


class ValidityChallengeType(str, Enum):
    """Types of validity challenges"""
    ANTICIPATION_102 = "anticipation_102"
    OBVIOUSNESS_103 = "obviousness_103"
    WRITTEN_DESCRIPTION_112 = "written_description_112"
    ENABLEMENT_112 = "enablement_112"
    INDEFINITENESS_112 = "indefiniteness_112"
    DOUBLE_PATENTING = "double_patenting"


class LikelihoodLevel(str, Enum):
    """Likelihood assessment levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ============================================================================
# INPUT/OUTPUT SCHEMAS
# ============================================================================

class PatentClassificationInput(BaseModel):
    """Input for patent document classification"""
    document_text: str = Field(..., description="Full text of the patent document")
    document_title: Optional[str] = Field(None, description="Title of the document")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PatentClassificationOutput(BaseModel):
    """Output from patent document classification"""
    document_type: PatentDocumentType = Field(..., description="Classified document type")
    patent_number: Optional[str] = Field(None, description="Extracted patent number")
    application_number: Optional[str] = Field(None, description="Extracted application number")
    filing_date: Optional[date] = Field(None, description="Extracted filing date")
    title: str = Field(..., description="Patent title")
    abstract: str = Field(..., description="Patent abstract")
    technology_area: str = Field(..., description="Primary technology area")
    ipc_classes: List[str] = Field(default_factory=list, description="International Patent Classification codes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")


class ClaimExtractionInput(BaseModel):
    """Input for patent claim extraction"""
    patent_text: str = Field(..., description="Full patent document text")
    patent_number: str = Field(..., description="Patent number")


class ExtractedClaim(BaseModel):
    """Individual extracted patent claim"""
    claim_number: int = Field(..., description="Claim number")
    claim_type: ClaimType = Field(..., description="Type of claim")
    claim_text: str = Field(..., description="Full claim text")
    dependencies: List[int] = Field(default_factory=list, description="Dependent claim numbers")
    key_limitations: List[str] = Field(default_factory=list, description="Key claim limitations")


class ClaimExtractionOutput(BaseModel):
    """Output from claim extraction"""
    claims: List[ExtractedClaim] = Field(..., description="Extracted claims")
    total_claims: int = Field(..., description="Total number of claims")
    independent_claims: int = Field(..., description="Number of independent claims")
    dependent_claims: int = Field(..., description="Number of dependent claims")


class InfringementAnalysisInput(BaseModel):
    """Input for infringement analysis"""
    patent_claims: List[str] = Field(..., description="Patent claims to analyze")
    accused_product_description: str = Field(..., description="Description of accused product/process")
    patent_number: str = Field(..., description="Patent number")
    claim_chart_data: Optional[Dict[str, Any]] = Field(None, description="Existing claim chart data")


class InfringementAnalysisOutput(BaseModel):
    """Output from infringement analysis"""
    infringement_likelihood: LikelihoodLevel = Field(..., description="Overall infringement likelihood")
    infringement_types: List[InfringementType] = Field(..., description="Potential infringement types")
    claim_by_claim_analysis: Dict[str, str] = Field(..., description="Analysis for each claim")
    key_limitations_met: List[str] = Field(..., description="Claim limitations met by accused product")
    key_limitations_not_met: List[str] = Field(..., description="Claim limitations not met")
    equivalents_analysis: str = Field(..., description="Doctrine of equivalents analysis")
    recommendation: str = Field(..., description="Overall recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")


class ValidityChallengeInput(BaseModel):
    """Input for validity challenge analysis"""
    patent_claims: List[str] = Field(..., description="Patent claims to challenge")
    prior_art_references: List[str] = Field(..., description="Prior art reference descriptions")
    patent_number: str = Field(..., description="Patent number")
    challenge_type: ValidityChallengeType = Field(..., description="Type of validity challenge")


class ValidityChallengeOutput(BaseModel):
    """Output from validity challenge analysis"""
    challenge_type: ValidityChallengeType = Field(..., description="Type of challenge")
    success_likelihood: LikelihoodLevel = Field(..., description="Likelihood of successful challenge")
    strongest_prior_art: List[str] = Field(..., description="Strongest prior art references")
    claim_by_claim_analysis: Dict[str, str] = Field(..., description="Validity analysis for each claim")
    key_differences: List[str] = Field(..., description="Key differences from prior art")
    obviousness_rationale: Optional[str] = Field(None, description="Obviousness analysis if applicable")
    recommendation: str = Field(..., description="Overall recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")

