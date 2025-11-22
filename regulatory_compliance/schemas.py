"""
Pydantic schemas for Regulatory Compliance LLM processing.
Provides type-safe data validation for compliance analysis, GDPR/CCPA processing, and regulatory mapping.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date, datetime


# ============================================================================
# ENUMS
# ============================================================================

class ComplianceFramework(str, Enum):
    """Regulatory compliance frameworks"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    SOC2 = "soc2"
    FERPA = "ferpa"
    GLBA = "glba"


class ComplianceStatus(str, Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNDER_REVIEW = "under_review"


class SeverityLevel(str, Enum):
    """Severity levels for compliance issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DSARRequestType(str, Enum):
    """Types of Data Subject Access Requests"""
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    RESTRICTION = "restriction"
    PORTABILITY = "portability"
    OBJECTION = "objection"
    AUTOMATED_DECISION = "automated_decision"


class DataCategory(str, Enum):
    """Categories of personal data"""
    PERSONAL_IDENTIFIABLE = "personal_identifiable"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    LOCATION = "location"
    BEHAVIORAL = "behavioral"
    CONTACT = "contact"


# ============================================================================
# INPUT/OUTPUT SCHEMAS
# ============================================================================

class RequirementMappingInput(BaseModel):
    """Input for mapping regulatory requirements to policies"""
    policy_text: str = Field(..., description="Organizational policy text")
    framework: ComplianceFramework = Field(..., description="Regulatory framework to map against")
    requirement_id: Optional[str] = Field(None, description="Specific requirement ID to check")


class RequirementMappingOutput(BaseModel):
    """Output from requirement mapping"""
    requirement_id: str = Field(..., description="Regulatory requirement identifier")
    requirement_text: str = Field(..., description="Full requirement text")
    requirement_category: str = Field(..., description="Category of requirement")
    compliance_status: ComplianceStatus = Field(..., description="Compliance status")
    policy_sections: List[str] = Field(..., description="Relevant policy sections")
    gap_analysis: str = Field(..., description="Analysis of compliance gaps")
    recommendations: List[str] = Field(..., description="Recommendations for compliance")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence score")


class DSARProcessingInput(BaseModel):
    """Input for processing Data Subject Access Requests"""
    request_text: str = Field(..., description="DSAR request text")
    request_type: DSARRequestType = Field(..., description="Type of DSAR")
    data_subject_info: Dict[str, Any] = Field(..., description="Information about the data subject")


class DSARProcessingOutput(BaseModel):
    """Output from DSAR processing"""
    request_type: DSARRequestType = Field(..., description="Classified request type")
    data_categories_requested: List[DataCategory] = Field(..., description="Categories of data requested")
    systems_to_search: List[str] = Field(..., description="Systems that need to be searched")
    estimated_scope: str = Field(..., description="Estimated scope of the request")
    deadline: Optional[date] = Field(None, description="Regulatory deadline for response")
    complexity_level: str = Field(..., description="Complexity level (simple, moderate, complex)")
    recommended_actions: List[str] = Field(..., description="Recommended actions to fulfill request")
    risk_assessment: str = Field(..., description="Risk assessment for this request")


class DataInventoryInput(BaseModel):
    """Input for data inventory analysis"""
    system_description: str = Field(..., description="Description of the system/process")
    data_flows: Optional[str] = Field(None, description="Description of data flows")
    purpose: str = Field(..., description="Purpose of data processing")


class DataInventoryOutput(BaseModel):
    """Output from data inventory analysis"""
    activity_name: str = Field(..., description="Name of the processing activity")
    data_categories: List[DataCategory] = Field(..., description="Categories of data processed")
    processing_purposes: List[str] = Field(..., description="Purposes of processing")
    legal_basis: str = Field(..., description="Legal basis for processing")
    data_sources: List[str] = Field(..., description="Sources of data")
    data_recipients: List[str] = Field(..., description="Recipients of data")
    retention_period: str = Field(..., description="Data retention period")
    security_measures: List[str] = Field(..., description="Security measures in place")
    cross_border_transfers: bool = Field(..., description="Whether data crosses borders")
    risk_level: SeverityLevel = Field(..., description="Overall risk level")


class RedactionAnalysisInput(BaseModel):
    """Input for document redaction analysis"""
    document_text: str = Field(..., description="Document text to analyze for redaction")
    redaction_rules: List[str] = Field(..., description="Redaction rules to apply")
    framework: ComplianceFramework = Field(..., description="Compliance framework")


class RedactionAnalysisOutput(BaseModel):
    """Output from redaction analysis"""
    redaction_items: List[Dict[str, Any]] = Field(..., description="Items to redact with positions")
    redaction_categories: List[str] = Field(..., description="Categories of information to redact")
    risk_if_not_redacted: SeverityLevel = Field(..., description="Risk if items not redacted")
    redacted_text: str = Field(..., description="Text with redactions applied")
    redaction_summary: str = Field(..., description="Summary of redactions made")


class ComplianceAlertInput(BaseModel):
    """Input for compliance alert generation"""
    activity_description: str = Field(..., description="Description of activity or finding")
    framework: ComplianceFramework = Field(..., description="Relevant compliance framework")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ComplianceAlertOutput(BaseModel):
    """Output from compliance alert analysis"""
    alert_type: str = Field(..., description="Type of compliance alert")
    severity: SeverityLevel = Field(..., description="Severity level")
    violation_description: str = Field(..., description="Description of potential violation")
    affected_requirements: List[str] = Field(..., description="Affected regulatory requirements")
    potential_impact: str = Field(..., description="Potential impact of violation")
    remediation_steps: List[str] = Field(..., description="Steps to remediate")
    deadline: Optional[date] = Field(None, description="Deadline for remediation")
    escalation_needed: bool = Field(..., description="Whether escalation is needed")

