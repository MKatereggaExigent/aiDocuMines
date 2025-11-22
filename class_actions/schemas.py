"""
Pydantic schemas for Class Actions LLM processing.
Defines structured inputs/outputs for mass claims and class action litigation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

from core.vertical_schemas import (
    BaseDocumentInput,
    BaseAnalysisOutput,
    RiskLevel,
)


# ============================================================================
# Enums
# ============================================================================

class CADocumentType(str, Enum):
    """Document types for class actions"""
    INTAKE_FORM = "intake_form"
    EVIDENCE_EMAIL = "evidence_email"
    EVIDENCE_CHAT = "evidence_chat"
    FINANCIAL_RECORD = "financial_record"
    COMMUNICATION = "communication"
    CONTRACT = "contract"
    POLICY = "policy"
    COURT_FILING = "court_filing"
    SETTLEMENT_AGREEMENT = "settlement_agreement"
    NOTICE = "notice"
    OTHER = "other"


class PIIType(str, Enum):
    """Types of PII to detect and redact"""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    ADDRESS = "address"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    DRIVER_LICENSE = "driver_license"
    PASSPORT = "passport"
    OTHER = "other"


class EvidenceRelevance(str, Enum):
    """Evidence relevance levels"""
    HIGHLY_RELEVANT = "highly_relevant"
    RELEVANT = "relevant"
    MARGINALLY_RELEVANT = "marginally_relevant"
    NOT_RELEVANT = "not_relevant"


# ============================================================================
# Document Classification
# ============================================================================

class CADocumentClassificationInput(BaseDocumentInput):
    """Input for classifying class action documents"""
    case_name: str = Field(..., description="Name of the class action case")
    case_type: str = Field(default="consumer_protection", description="Type of class action case")


class CADocumentClassificationOutput(BaseAnalysisOutput):
    """Output from document classification"""
    ca_document_type: CADocumentType = Field(..., description="Classified document type")
    evidence_type: Optional[str] = Field(None, description="Specific evidence type if applicable")
    relevance: EvidenceRelevance = Field(..., description="Relevance to the case")
    contains_pii: bool = Field(False, description="Whether document contains PII")
    privilege_status: str = Field("none", description="Privilege status")
    recommended_action: str = Field(..., description="Recommended next action")


# ============================================================================
# PII Detection and Redaction
# ============================================================================

class PIIInstance(BaseModel):
    """Single instance of detected PII"""
    pii_type: PIIType = Field(..., description="Type of PII detected")
    original_text: str = Field(..., description="Original text containing PII")
    redacted_text: str = Field(..., description="Redacted version")
    page_number: int = Field(..., description="Page number where found")
    position_start: Optional[int] = Field(None, description="Start position in text")
    position_end: Optional[int] = Field(None, description="End position in text")
    confidence_score: float = Field(..., description="Detection confidence (0.0-1.0)")


class PIIDetectionInput(BaseDocumentInput):
    """Input for PII detection"""
    case_name: str = Field(..., description="Name of the class action case")
    pii_types_to_detect: List[str] = Field(default_factory=lambda: ["all"], description="Specific PII types to detect")


class PIIDetectionOutput(BaseAnalysisOutput):
    """Output from PII detection"""
    pii_instances: List[PIIInstance] = Field(default_factory=list, description="Detected PII instances")
    total_pii_found: int = Field(0, description="Total number of PII instances found")
    requires_redaction: bool = Field(False, description="Whether redaction is required")
    redaction_summary: str = Field("", description="Summary of redaction needs")


# ============================================================================
# Evidence Culling and Relevance
# ============================================================================

class EvidenceCullingInput(BaseDocumentInput):
    """Input for evidence culling"""
    case_name: str = Field(..., description="Name of the class action case")
    case_type: str = Field(..., description="Type of class action case")
    key_issues: List[str] = Field(default_factory=list, description="Key issues in the case")
    date_range_start: Optional[str] = Field(None, description="Start date for relevance")
    date_range_end: Optional[str] = Field(None, description="End date for relevance")


class EvidenceCullingOutput(BaseAnalysisOutput):
    """Output from evidence culling"""
    relevance_score: float = Field(..., description="Relevance score (0.0-1.0)")
    relevance_level: EvidenceRelevance = Field(..., description="Relevance classification")
    should_cull: bool = Field(False, description="Whether to cull this document")
    cull_reason: str = Field("", description="Reason for culling if applicable")
    key_topics: List[str] = Field(default_factory=list, description="Key topics found in document")
    relevant_excerpts: List[str] = Field(default_factory=list, description="Relevant text excerpts")


# ============================================================================
# Duplicate Detection
# ============================================================================

class DuplicateDetectionInput(BaseModel):
    """Input for duplicate detection"""
    claimant_data: Dict[str, Any] = Field(..., description="Claimant form data")
    existing_claims: List[Dict[str, Any]] = Field(default_factory=list, description="Existing claims to compare against")
    case_name: str = Field(..., description="Name of the class action case")


class DuplicateMatch(BaseModel):
    """Single duplicate match"""
    claimant_id: str = Field(..., description="ID of potential duplicate")
    similarity_score: float = Field(..., description="Similarity score (0.0-1.0)")
    matching_fields: List[str] = Field(default_factory=list, description="Fields that match")
    is_likely_duplicate: bool = Field(False, description="Whether this is likely a duplicate")


class DuplicateDetectionOutput(BaseAnalysisOutput):
    """Output from duplicate detection"""
    is_duplicate: bool = Field(False, description="Whether this is a duplicate")
    duplicate_matches: List[DuplicateMatch] = Field(default_factory=list, description="Potential duplicate matches")
    best_match_score: float = Field(0.0, description="Highest similarity score")
    recommendation: str = Field("", description="Recommendation on how to handle")

