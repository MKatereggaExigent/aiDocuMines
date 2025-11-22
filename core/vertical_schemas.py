"""
Base Pydantic models for vertical apps.
Provides structured validation and type safety for LLM inputs/outputs.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Base Models
# ============================================================================

class BaseDocumentInput(BaseModel):
    """Base input for document processing"""
    document_text: str = Field(..., description="The document text to process")
    document_id: Optional[int] = Field(None, description="File ID from database")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "This is a sample contract...",
                "document_id": 123,
                "metadata": {"source": "data_room"}
            }
        }


class BaseAnalysisOutput(BaseModel):
    """Base output for analysis results"""
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reasoning: str = Field(..., description="Explanation of the analysis")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0 and 1')
        return v


# ============================================================================
# Document Classification
# ============================================================================

class DocumentType(str, Enum):
    """Common document types across verticals"""
    NDA = "nda"
    CONTRACT = "contract"
    AGREEMENT = "agreement"
    FINANCIAL = "financial_statement"
    LEGAL = "legal_document"
    COMPLIANCE = "compliance_document"
    OTHER = "other"


class DocumentClassificationInput(BaseDocumentInput):
    """Input for document classification"""
    possible_types: Optional[List[str]] = Field(None, description="Limit classification to these types")


class DocumentClassificationOutput(BaseAnalysisOutput):
    """Output for document classification"""
    document_type: str = Field(..., description="Classified document type")
    sub_type: Optional[str] = Field(None, description="More specific sub-type")
    key_indicators: List[str] = Field(default_factory=list, description="Key phrases that led to classification")


# ============================================================================
# Risk Analysis
# ============================================================================

class RiskLevel(str, Enum):
    """Risk severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class RiskClauseInput(BaseDocumentInput):
    """Input for risk clause extraction"""
    focus_areas: Optional[List[str]] = Field(None, description="Specific risk areas to focus on")


class RiskClauseOutput(BaseAnalysisOutput):
    """Output for a single risk clause"""
    clause_text: str = Field(..., description="The risky clause text")
    risk_level: RiskLevel = Field(..., description="Severity of the risk")
    risk_category: str = Field(..., description="Category of risk (e.g., 'financial', 'legal')")
    impact_description: str = Field(..., description="Description of potential impact")
    mitigation_suggestions: List[str] = Field(default_factory=list, description="Suggested mitigations")
    page_number: Optional[int] = Field(None, description="Page number where clause appears")
    section: Optional[str] = Field(None, description="Section name where clause appears")


class RiskAnalysisOutput(BaseModel):
    """Complete risk analysis output"""
    risk_clauses: List[RiskClauseOutput] = Field(default_factory=list, description="All identified risk clauses")
    overall_risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score")
    summary: str = Field(..., description="Executive summary of risks")
    recommendations: List[str] = Field(default_factory=list, description="High-level recommendations")


# ============================================================================
# Entity Extraction
# ============================================================================

class EntityType(str, Enum):
    """Common entity types"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    MONEY = "money"
    PERCENTAGE = "percentage"
    LEGAL_REFERENCE = "legal_reference"


class ExtractedEntity(BaseModel):
    """A single extracted entity"""
    text: str = Field(..., description="The entity text")
    entity_type: EntityType = Field(..., description="Type of entity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    context: Optional[str] = Field(None, description="Surrounding context")
    start_pos: Optional[int] = Field(None, description="Start position in text")
    end_pos: Optional[int] = Field(None, description="End position in text")


class EntityExtractionOutput(BaseModel):
    """Output for entity extraction"""
    entities: List[ExtractedEntity] = Field(default_factory=list, description="All extracted entities")
    entity_count: int = Field(..., description="Total number of entities")
    entity_summary: Dict[str, int] = Field(default_factory=dict, description="Count by entity type")


# ============================================================================
# Key Information Extraction
# ============================================================================

class KeyValuePair(BaseModel):
    """A key-value pair extracted from document"""
    key: str = Field(..., description="The field name")
    value: str = Field(..., description="The extracted value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source_text: Optional[str] = Field(None, description="Source text where found")


class KeyInformationOutput(BaseModel):
    """Output for key information extraction"""
    key_values: List[KeyValuePair] = Field(default_factory=list, description="Extracted key-value pairs")
    summary: str = Field(..., description="Summary of key information")

