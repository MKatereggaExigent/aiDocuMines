"""
LLM Service Layer for Class Actions using DSPy.
Handles all LLM-powered processing for mass claims and class action litigation.
"""
import dspy
import json
import logging
from typing import List, Dict, Any, Optional

from .dspy_signatures import (
    ClassifyCADocument,
    DetectPII,
    CullEvidence,
    DetectDuplicateClaims,
    ValidateIntakeForm,
)
from .models import (
    EvidenceDocument,
    PIIRedaction,
    IntakeForm,
    MassClaimsRun,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Document Classification Service
# ============================================================================

class CADocumentClassifier:
    """Classifies documents for class action litigation"""
    
    def __init__(self):
        self.classifier = dspy.ChainOfThought(ClassifyCADocument)
    
    def classify(
        self,
        document_text: str,
        file_id: int,
        user,
        mass_claims_run: MassClaimsRun,
        case_name: str = "",
        case_type: str = "consumer_protection",
    ) -> EvidenceDocument:
        """Classify an evidence document and save to database"""
        try:
            result = self.classifier(
                document_text=document_text[:10000],
                case_name=case_name or mass_claims_run.case_name,
                case_type=case_type or mass_claims_run.case_type,
            )
            
            confidence = float(result.confidence_score) if result.confidence_score else 0.5
            relevance_score = float(result.relevance_score) if result.relevance_score else 0.5
            
            evidence_doc = EvidenceDocument.objects.create(
                client=user.client,
                file_id=file_id,
                user=user,
                mass_claims_run=mass_claims_run,
                evidence_type=result.evidence_type or 'document',
                is_culled=result.relevance == 'not_relevant',
                cull_reason=f"Low relevance: {result.relevance}" if result.relevance == 'not_relevant' else "",
                relevance_score=relevance_score,
                contains_pii=result.contains_pii == 'true',
                privilege_status=result.privilege_status or 'none',
                processing_metadata={
                    'document_type': result.document_type,
                    'recommended_action': result.recommended_action,
                    'reasoning': result.reasoning,
                    'confidence': confidence,
                },
            )
            
            logger.info(f"Classified evidence document {file_id} with relevance {relevance_score}")
            return evidence_doc
            
        except Exception as e:
            logger.error(f"Error classifying document {file_id}: {e}")
            raise


# ============================================================================
# PII Detection Service
# ============================================================================

class CAPIIDetector:
    """Detects and redacts PII in class action documents"""
    
    def __init__(self):
        self.detector = dspy.ChainOfThought(DetectPII)
    
    def detect_pii(
        self,
        document_text: str,
        file_id: int,
        user,
        mass_claims_run: MassClaimsRun,
        pii_types: List[str] = None,
    ) -> List[PIIRedaction]:
        """Detect PII in a document and save redactions to database"""
        try:
            result = self.detector(
                document_text=document_text[:15000],
                case_name=mass_claims_run.case_name,
                pii_types_to_detect=','.join(pii_types) if pii_types else 'all',
            )
            
            try:
                pii_instances = json.loads(result.pii_instances_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse PII instances for file {file_id}")
                pii_instances = []
            
            redactions = []
            for pii_data in pii_instances:
                try:
                    redaction = PIIRedaction.objects.create(
                        client=user.client,
                        file_id=file_id,
                        user=user,
                        mass_claims_run=mass_claims_run,
                        pii_type=pii_data.get('pii_type', 'other'),
                        original_text=pii_data.get('original_text', ''),
                        redacted_text=pii_data.get('redacted_text', '[REDACTED]'),
                        page_number=pii_data.get('page_number', 1),
                        position_start=pii_data.get('position_start'),
                        position_end=pii_data.get('position_end'),
                        confidence_score=pii_data.get('confidence_score', 0.8),
                    )
                    redactions.append(redaction)
                except Exception as e:
                    logger.error(f"Error creating PII redaction: {e}")
                    continue
            
            logger.info(f"Detected {len(redactions)} PII instances in document {file_id}")
            return redactions
            
        except Exception as e:
            logger.error(f"Error detecting PII in document {file_id}: {e}")
            raise


# ============================================================================
# Duplicate Detection Service
# ============================================================================

class CADuplicateDetector:
    """Detects duplicate claimant submissions"""
    
    def __init__(self):
        self.detector = dspy.ChainOfThought(DetectDuplicateClaims)
    
    def detect_duplicates(
        self,
        intake_form: IntakeForm,
        existing_claims: List[IntakeForm],
    ) -> Dict[str, Any]:
        """Detect if an intake form is a duplicate"""
        try:
            existing_claims_data = [
                {'claimant_id': str(claim.claimant_id), 'data': claim.claimant_data}
                for claim in existing_claims[:50]  # Limit to 50 for performance
            ]
            
            result = self.detector(
                claimant_data_json=json.dumps(intake_form.claimant_data),
                existing_claims_json=json.dumps(existing_claims_data),
                case_name=intake_form.mass_claims_run.case_name,
            )
            
            return {
                'is_duplicate': result.is_duplicate == 'true',
                'best_match_score': float(result.best_match_score) if result.best_match_score else 0.0,
                'recommendation': result.recommendation,
                'reasoning': result.reasoning,
            }
            
        except Exception as e:
            logger.error(f"Error detecting duplicates for intake form {intake_form.id}: {e}")
            raise

