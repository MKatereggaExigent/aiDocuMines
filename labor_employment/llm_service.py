"""
LLM Service Layer for Labor & Employment using DSPy.
Handles all LLM-powered processing for workplace communications and employment matters.
"""
import dspy
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .dspy_signatures import (
    AnalyzeCommunication,
    AnalyzePolicyCompliance,
    AnalyzeWageHour,
    DetectCommunicationPatterns,
)
from .models import (
    CommunicationMessage,
    PolicyComparison,
    WageHourAnalysis,
    CommunicationPattern,
    WorkplaceCommunicationsRun,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Communication Analysis Service
# ============================================================================

class LECommunicationAnalyzer:
    """Analyzes workplace communications for sentiment, toxicity, and compliance"""
    
    def __init__(self):
        self.analyzer = dspy.ChainOfThought(AnalyzeCommunication)
    
    def analyze(
        self,
        message_content: str,
        file_id: int,
        user,
        communications_run: WorkplaceCommunicationsRun,
        message_type: str = "email",
        sender: str = "",
        recipients: List[str] = None,
        sent_datetime: datetime = None,
    ) -> CommunicationMessage:
        """Analyze a communication message and save to database"""
        try:
            result = self.analyzer(
                message_content=message_content[:10000],
                message_type=message_type,
                sender=sender,
                recipients=','.join(recipients or []),
                case_type=communications_run.case_type,
            )
            
            sentiment_score = float(result.sentiment_score) if result.sentiment_score else 0.0
            toxicity_score = float(result.toxicity_score) if result.toxicity_score else 0.0
            relevance_score = float(result.relevance_score) if result.relevance_score else 0.5
            
            message = CommunicationMessage.objects.create(
                client=user.client,
                file_id=file_id,
                user=user,
                communications_run=communications_run,
                message_id=f"msg_{file_id}_{sent_datetime.timestamp() if sent_datetime else 'unknown'}",
                message_type=message_type,
                sender=sender,
                recipients=recipients or [],
                content=message_content,
                sent_datetime=sent_datetime or datetime.now(),
                sentiment_score=sentiment_score,
                toxicity_score=toxicity_score,
                relevance_score=relevance_score,
                is_privileged=result.is_privileged == 'true',
                contains_pii=result.contains_pii == 'true',
                is_flagged=result.is_flagged == 'true',
                flag_reason=result.flag_reason or '',
                processing_metadata={
                    'sentiment_level': result.sentiment_level,
                    'toxicity_level': result.toxicity_level,
                    'key_topics': result.key_topics.split(',') if result.key_topics else [],
                    'confidence': float(result.confidence_score) if result.confidence_score else 0.5,
                    'reasoning': result.reasoning,
                },
            )
            
            logger.info(f"Analyzed communication {file_id} with sentiment {sentiment_score}, toxicity {toxicity_score}")
            return message
            
        except Exception as e:
            logger.error(f"Error analyzing communication {file_id}: {e}")
            raise


# ============================================================================
# Policy Compliance Service
# ============================================================================

class LEPolicyComplianceAnalyzer:
    """Analyzes policy compliance based on workplace communications"""
    
    def __init__(self):
        self.analyzer = dspy.ChainOfThought(AnalyzePolicyCompliance)
    
    def analyze(
        self,
        policy_text: str,
        policy_type: str,
        user,
        communications_run: WorkplaceCommunicationsRun,
        communications_sample: List[str],
        policy_file_id: int,
    ) -> PolicyComparison:
        """Analyze policy compliance and save to database"""
        try:
            result = self.analyzer(
                policy_text=policy_text[:15000],
                policy_type=policy_type,
                communications_sample='\n---\n'.join(communications_sample[:20]),
                company_name=communications_run.company_name,
            )
            
            try:
                violations = json.loads(result.violations_json)
            except json.JSONDecodeError:
                violations = []
            
            try:
                gaps = json.loads(result.gaps_json)
            except json.JSONDecodeError:
                gaps = []
            
            try:
                recommendations = json.loads(result.recommendations_json)
            except json.JSONDecodeError:
                recommendations = []
            
            compliance_score = float(result.compliance_score) if result.compliance_score else 0.5
            
            policy_comparison = PolicyComparison.objects.create(
                client=user.client,
                user=user,
                communications_run=communications_run,
                policy_name=f"{policy_type.replace('_', ' ').title()} Policy",
                policy_type=policy_type,
                policy_document_id=policy_file_id,
                policy_text=policy_text,
                compliance_score=compliance_score,
                violations_found=violations,
                policy_gaps=gaps,
                recommendations=recommendations,
                analysis_metadata={
                    'confidence': float(result.confidence_score) if result.confidence_score else 0.5,
                    'reasoning': result.reasoning,
                },
            )
            
            logger.info(f"Analyzed policy compliance with score {compliance_score}")
            return policy_comparison
            
        except Exception as e:
            logger.error(f"Error analyzing policy compliance: {e}")
            raise

