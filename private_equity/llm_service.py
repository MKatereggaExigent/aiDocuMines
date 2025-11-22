"""
LLM Service Layer for Private Equity using DSPy.
Handles all LLM-powered processing for PE due diligence.
"""
import dspy
import json
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

from .dspy_signatures import (
    ClassifyPEDocument,
    ExtractPERiskClauses,
    GenerateDDFindings,
    AnswerPEQuestion,
    ExtractPEKeyInfo,
)
from .schemas import (
    PEDocumentClassificationInput,
    PEDocumentClassificationOutput,
    PERiskClauseInput,
    PERiskClauseOutput,
    RiskAnalysisOutput,
    DDFindingInput,
    DDFindingsOutput,
    PEDocumentType,
    PERiskCategory,
    RiskLevel,
)
from .models import (
    DocumentClassification,
    RiskClause,
    FindingsReport,
    DueDiligenceRun,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DSPy Configuration
# ============================================================================

def configure_dspy():
    """Configure DSPy with the appropriate LLM"""
    try:
        # Try to use Ollama first (local)
        lm = dspy.OllamaLocal(
            model=getattr(settings, 'DSPY_MODEL', 'llama3'),
            base_url=getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
            max_tokens=4000,
        )
        dspy.settings.configure(lm=lm)
        logger.info("DSPy configured with Ollama")
    except Exception as e:
        logger.warning(f"Failed to configure Ollama: {e}. Falling back to OpenAI.")
        try:
            # Fallback to OpenAI
            lm = dspy.OpenAI(
                model=getattr(settings, 'OPENAI_MODEL', 'gpt-4'),
                api_key=getattr(settings, 'OPENAI_API_KEY', ''),
                max_tokens=4000,
            )
            dspy.settings.configure(lm=lm)
            logger.info("DSPy configured with OpenAI")
        except Exception as e2:
            logger.error(f"Failed to configure DSPy: {e2}")
            raise


# Initialize DSPy on module load
try:
    configure_dspy()
except Exception as e:
    logger.error(f"Failed to initialize DSPy: {e}")


# ============================================================================
# Document Classification Service
# ============================================================================

class PEDocumentClassifier:
    """Classifies documents for PE due diligence"""
    
    def __init__(self):
        self.classifier = dspy.ChainOfThought(ClassifyPEDocument)
    
    def classify(
        self,
        document_text: str,
        file_id: int,
        user,
        dd_run: DueDiligenceRun,
        deal_name: str = "",
        target_company: str = "",
    ) -> DocumentClassification:
        """
        Classify a document and save to database.
        
        Args:
            document_text: The document text to classify
            file_id: ID of the file being classified
            user: User performing the classification
            dd_run: Due diligence run this belongs to
            deal_name: Name of the deal
            target_company: Target company name
            
        Returns:
            DocumentClassification instance
        """
        try:
            # Run DSPy classification
            result = self.classifier(
                document_text=document_text[:10000],  # Limit to first 10k chars
                deal_name=deal_name or dd_run.deal_name,
                target_company=target_company or dd_run.target_company,
            )
            
            # Parse confidence score
            try:
                confidence = float(result.confidence_score)
            except (ValueError, TypeError):
                confidence = 0.5
            
            # Parse key indicators
            try:
                if isinstance(result.key_indicators, str):
                    key_indicators = [k.strip() for k in result.key_indicators.split(',')]
                else:
                    key_indicators = list(result.key_indicators)
            except:
                key_indicators = []
            
            # Create and save classification
            classification = DocumentClassification.objects.create(
                client=user.client,
                file_id=file_id,
                user=user,
                due_diligence_run=dd_run,
                document_type=result.document_type,
                confidence_score=confidence,
                classification_metadata={
                    'sub_type': result.sub_type,
                    'key_indicators': key_indicators,
                    'relevance_to_dd': result.relevance_to_dd,
                    'priority': result.priority,
                    'recommended_reviewers': result.recommended_reviewers.split(',') if isinstance(result.recommended_reviewers, str) else result.recommended_reviewers,
                    'reasoning': result.reasoning,
                },
            )
            
            logger.info(f"Classified document {file_id} as {result.document_type} with confidence {confidence}")
            return classification

        except Exception as e:
            logger.error(f"Error classifying document {file_id}: {e}")
            raise


# ============================================================================
# Risk Clause Extraction Service
# ============================================================================

class PERiskExtractor:
    """Extracts and analyzes risk clauses from PE documents"""

    def __init__(self):
        self.extractor = dspy.ChainOfThought(ExtractPERiskClauses)

    def extract_risks(
        self,
        document_text: str,
        file_id: int,
        user,
        dd_run: DueDiligenceRun,
        document_type: str = "",
        deal_type: str = "acquisition",
        focus_areas: List[str] = None,
    ) -> List[RiskClause]:
        """
        Extract risk clauses from a document and save to database.

        Args:
            document_text: The document text to analyze
            file_id: ID of the file being analyzed
            user: User performing the analysis
            dd_run: Due diligence run this belongs to
            document_type: Type of document
            deal_type: Type of deal
            focus_areas: Specific risk areas to focus on

        Returns:
            List of RiskClause instances
        """
        try:
            # Run DSPy risk extraction
            result = self.extractor(
                document_text=document_text[:15000],  # Limit to first 15k chars
                document_type=document_type,
                deal_type=deal_type or dd_run.deal_type,
                target_company=dd_run.target_company,
                focus_areas=','.join(focus_areas) if focus_areas else "",
            )

            # Parse risk clauses JSON
            try:
                risk_clauses_data = json.loads(result.risk_clauses_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse risk clauses JSON for file {file_id}")
                risk_clauses_data = []

            # Create RiskClause objects
            risk_clauses = []
            for clause_data in risk_clauses_data:
                try:
                    risk_clause = RiskClause.objects.create(
                        client=user.client,
                        file_id=file_id,
                        user=user,
                        due_diligence_run=dd_run,
                        clause_type=clause_data.get('risk_category', 'other'),
                        clause_text=clause_data.get('clause_text', ''),
                        risk_level=clause_data.get('risk_level', 'medium'),
                        impact_description=clause_data.get('impact_description', ''),
                        mitigation_suggestion=', '.join(clause_data.get('mitigation_suggestions', [])),
                        page_number=clause_data.get('page_number'),
                        section_reference=clause_data.get('section', ''),
                        confidence_score=0.8,  # Default confidence
                        metadata={
                            'deal_impact': result.deal_impact,
                            'overall_risk_score': result.overall_risk_score,
                        },
                    )
                    risk_clauses.append(risk_clause)
                except Exception as e:
                    logger.error(f"Error creating risk clause: {e}")
                    continue

            logger.info(f"Extracted {len(risk_clauses)} risk clauses from document {file_id}")
            return risk_clauses

        except Exception as e:
            logger.error(f"Error extracting risks from document {file_id}: {e}")
            raise


# ============================================================================
# Due Diligence Findings Generator
# ============================================================================

class PEFindingsGenerator:
    """Generates comprehensive DD findings reports"""

    def __init__(self):
        self.generator = dspy.ChainOfThought(GenerateDDFindings)

    def generate_findings(
        self,
        dd_run: DueDiligenceRun,
        user,
        focus_areas: List[str] = None,
    ) -> FindingsReport:
        """
        Generate comprehensive findings report for a DD run.

        Args:
            dd_run: Due diligence run to generate findings for
            user: User generating the report
            focus_areas: Specific areas to focus on

        Returns:
            FindingsReport instance
        """
        try:
            # Gather data from DD run
            classifications = dd_run.document_classifications.all()
            risk_clauses = dd_run.risk_clauses.all()

            # Prepare document summary
            doc_summary = {}
            for classification in classifications:
                doc_type = classification.document_type
                doc_summary[doc_type] = doc_summary.get(doc_type, 0) + 1

            # Prepare risk summary
            risk_summary = {}
            for risk in risk_clauses:
                risk_cat = risk.clause_type
                risk_summary[risk_cat] = risk_summary.get(risk_cat, 0) + 1

            # Get key documents
            key_docs = [c.file.filename for c in classifications[:10]]

            # Run DSPy findings generation
            result = self.generator(
                deal_name=dd_run.deal_name,
                target_company=dd_run.target_company,
                deal_type=dd_run.deal_type,
                document_summary=json.dumps(doc_summary),
                risk_summary=json.dumps(risk_summary),
                key_documents=', '.join(key_docs),
                focus_areas=', '.join(focus_areas) if focus_areas else "",
            )

            # Parse findings and recommendations
            try:
                key_findings = json.loads(result.key_findings_json)
            except json.JSONDecodeError:
                key_findings = []

            try:
                recommendations = json.loads(result.recommendations_json)
            except json.JSONDecodeError:
                recommendations = []

            # Create FindingsReport
            report = FindingsReport.objects.create(
                client=user.client,
                due_diligence_run=dd_run,
                user=user,
                report_name=f"Due Diligence Findings - {dd_run.deal_name}",
                executive_summary=result.executive_summary,
                document_summary=doc_summary,
                risk_summary=risk_summary,
                key_findings=key_findings,
                recommendations=recommendations,
                overall_risk_level=result.overall_risk_assessment,
                confidence_score=float(result.confidence_score) if result.confidence_score else 0.8,
                metadata={
                    'deal_recommendation': result.deal_recommendation,
                    'reasoning': result.reasoning,
                },
            )

            logger.info(f"Generated findings report for DD run {dd_run.id}")
            return report

        except Exception as e:
            logger.error(f"Error generating findings for DD run {dd_run.id}: {e}")
            raise

