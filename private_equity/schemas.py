"""
Pydantic schemas for Private Equity vertical app.
Defines structured inputs/outputs for LLM processing with dspy.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import base schemas
from core.vertical_schemas import (
    BaseDocumentInput,
    BaseAnalysisOutput,
    DocumentClassificationInput,
    DocumentClassificationOutput,
    RiskLevel,
    RiskClauseInput,
    RiskClauseOutput,
    RiskAnalysisOutput,
)


# ============================================================================
# Private Equity Specific Document Types
# ============================================================================

class PEDocumentType(str, Enum):
    """Document types specific to Private Equity due diligence"""
    NDA = "nda"
    SUPPLIER_CONTRACT = "supplier_contract"
    EMPLOYMENT_AGREEMENT = "employment_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    IP_DOCUMENT = "ip_document"
    PRIVACY_POLICY = "privacy_policy"
    FINANCIAL_STATEMENT = "financial_statement"
    AUDIT_REPORT = "audit_report"
    INSURANCE_POLICY = "insurance_policy"
    REGULATORY_FILING = "regulatory_filing"
    SHAREHOLDER_AGREEMENT = "shareholder_agreement"
    LOAN_AGREEMENT = "loan_agreement"
    SECURITY_AGREEMENT = "security_agreement"
    OTHER = "other"


# ============================================================================
# Document Classification for PE
# ============================================================================

class PEDocumentClassificationInput(DocumentClassificationInput):
    """Input for PE document classification"""
    deal_name: Optional[str] = Field(None, description="Name of the deal/transaction")
    target_company: Optional[str] = Field(None, description="Target company name")
    data_room_path: Optional[str] = Field(None, description="Path in data room")


class PEDocumentClassificationOutput(DocumentClassificationOutput):
    """Output for PE document classification"""
    pe_document_type: PEDocumentType = Field(..., description="PE-specific document type")
    relevance_to_dd: float = Field(..., ge=0.0, le=1.0, description="Relevance to due diligence")
    recommended_reviewers: List[str] = Field(default_factory=list, description="Recommended reviewer roles")
    priority: str = Field(..., description="Review priority: critical, high, medium, low")


# ============================================================================
# Risk Clause Extraction for PE
# ============================================================================

class PERiskCategory(str, Enum):
    """Risk categories specific to PE due diligence"""
    CHANGE_OF_CONTROL = "change_of_control"
    ASSIGNMENT = "assignment"
    TERMINATION = "termination"
    INDEMNITY = "indemnity"
    NON_COMPETE = "non_compete"
    CONFIDENTIALITY = "confidentiality"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    ENVIRONMENTAL = "environmental"
    LITIGATION = "litigation"
    IP_RIGHTS = "ip_rights"
    EMPLOYMENT = "employment"
    TAX = "tax"
    OTHER = "other"


class PERiskClauseInput(RiskClauseInput):
    """Input for PE risk clause extraction"""
    deal_type: Optional[str] = Field(None, description="Type of deal: acquisition, merger, investment, divestiture")
    target_company: Optional[str] = Field(None, description="Target company name")


class PERiskClauseOutput(RiskClauseOutput):
    """Output for PE risk clause extraction"""
    pe_risk_category: PERiskCategory = Field(..., description="PE-specific risk category")
    deal_impact: str = Field(..., description="Impact on the deal")
    requires_legal_review: bool = Field(..., description="Whether legal review is required")
    estimated_financial_impact: Optional[str] = Field(None, description="Estimated financial impact if quantifiable")


# ============================================================================
# Due Diligence Findings
# ============================================================================

class DDFindingInput(BaseDocumentInput):
    """Input for generating due diligence findings"""
    deal_name: str = Field(..., description="Name of the deal")
    target_company: str = Field(..., description="Target company name")
    document_classifications: List[Dict[str, Any]] = Field(default_factory=list, description="Classified documents")
    risk_clauses: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted risk clauses")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")


class DDKeyFinding(BaseModel):
    """A single key finding from due diligence"""
    title: str = Field(..., description="Finding title")
    description: str = Field(..., description="Detailed description")
    severity: RiskLevel = Field(..., description="Severity level")
    category: str = Field(..., description="Finding category")
    supporting_documents: List[str] = Field(default_factory=list, description="Supporting document names")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class DDRecommendation(BaseModel):
    """A recommendation from due diligence"""
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed description")
    priority: str = Field(..., description="Priority: critical, high, medium, low")
    action_items: List[str] = Field(default_factory=list, description="Specific action items")
    responsible_party: Optional[str] = Field(None, description="Who should handle this")


class DDFindingsOutput(BaseAnalysisOutput):
    """Output for due diligence findings report"""
    executive_summary: str = Field(..., description="Executive summary of findings")
    key_findings: List[DDKeyFinding] = Field(default_factory=list, description="Key findings")
    recommendations: List[DDRecommendation] = Field(default_factory=list, description="Recommendations")
    document_summary: Dict[str, int] = Field(default_factory=dict, description="Summary of documents by type")
    risk_summary: Dict[str, int] = Field(default_factory=dict, description="Summary of risks by category")
    overall_risk_assessment: str = Field(..., description="Overall risk assessment")
    deal_recommendation: str = Field(..., description="Proceed/Caution/Stop recommendation with reasoning")

