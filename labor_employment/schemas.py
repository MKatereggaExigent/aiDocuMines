"""
Pydantic schemas for Labor & Employment LLM processing.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from core.vertical_schemas import BaseDocumentInput, BaseAnalysisOutput


# ============================================================================
# Enums
# ============================================================================

class LEMessageType(str, Enum):
    """Types of workplace communications"""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    CHAT = "chat"
    SMS = "sms"
    OTHER = "other"


class SentimentLevel(str, Enum):
    """Sentiment levels"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class ToxicityLevel(str, Enum):
    """Toxicity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class ComplianceIssueType(str, Enum):
    """Types of compliance issues"""
    HARASSMENT = "harassment"
    DISCRIMINATION = "discrimination"
    RETALIATION = "retaliation"
    WAGE_HOUR = "wage_hour"
    PRIVACY = "privacy"
    SAFETY = "safety"
    POLICY_VIOLATION = "policy_violation"
    OTHER = "other"


# ============================================================================
# Communication Analysis Schemas
# ============================================================================

class LECommunicationInput(BaseDocumentInput):
    """Input for analyzing workplace communication"""
    message_type: LEMessageType
    sender: str
    recipients: List[str]
    subject: Optional[str] = None
    sent_datetime: str
    case_type: str = "discrimination"


class LECommunicationOutput(BaseAnalysisOutput):
    """Output from communication analysis"""
    sentiment_level: SentimentLevel
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    toxicity_level: ToxicityLevel
    toxicity_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    is_privileged: bool
    contains_pii: bool
    is_flagged: bool
    flag_reason: Optional[str] = None
    key_topics: List[str]


# ============================================================================
# Policy Compliance Schemas
# ============================================================================

class LEPolicyComplianceInput(BaseModel):
    """Input for policy compliance analysis"""
    policy_text: str
    policy_type: str
    communications_sample: List[str]
    company_name: str


class PolicyViolation(BaseModel):
    """A single policy violation"""
    violation_type: str
    severity: str  # low, medium, high, critical
    description: str
    evidence: str
    recommendation: str


class LEPolicyComplianceOutput(BaseAnalysisOutput):
    """Output from policy compliance analysis"""
    compliance_score: float = Field(ge=0.0, le=1.0)
    violations: List[PolicyViolation]
    gaps: List[str]
    recommendations: List[str]


# ============================================================================
# Wage & Hour Analysis Schemas
# ============================================================================

class LEWageHourInput(BaseModel):
    """Input for wage & hour analysis"""
    employee_name: str
    job_title: str
    hourly_rate: Optional[float] = None
    analysis_period_days: int
    early_morning_messages: int
    late_evening_messages: int
    weekend_messages: int
    total_hours_worked: float


class LEWageHourOutput(BaseAnalysisOutput):
    """Output from wage & hour analysis"""
    potential_overtime_violations: bool
    potential_break_violations: bool
    potential_meal_violations: bool
    estimated_unpaid_hours: float
    estimated_unpaid_amount: Optional[float] = None
    violation_details: List[str]
    recommendations: List[str]


# ============================================================================
# Pattern Detection Schemas
# ============================================================================

class LEPatternInput(BaseModel):
    """Input for communication pattern detection"""
    communications: List[Dict[str, Any]]
    key_personnel: List[str]
    case_type: str
    analysis_period: str


class CommunicationPattern(BaseModel):
    """A detected communication pattern"""
    pattern_type: str
    description: str
    severity_score: float = Field(ge=0.0, le=1.0)
    participants: List[str]
    frequency: int
    evidence_messages: List[str]


class LEPatternOutput(BaseAnalysisOutput):
    """Output from pattern detection"""
    patterns: List[CommunicationPattern]
    risk_assessment: str
    recommendations: List[str]

