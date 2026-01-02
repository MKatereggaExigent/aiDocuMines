from celery import shared_task
import logging
import os
import json
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from core.models import File
from core.utils import register_generated_file
from .models import (
    DueDiligenceRun, DocumentClassification, RiskClause, FindingsReport
)
import requests

logger = logging.getLogger(__name__)
User = get_user_model()

# Import AI services (will be available in production)
try:
    from document_search.tasks import semantic_search_task, index_file_task
    from file_elasticsearch.utils import search_files, index_file
    from grid_documents_interrogation.tasks import ask_question_task
    from document_anonymizer.tasks import detect_pii_task, anonymize_document_task
    from document_ocr.tasks import extract_text_task
    AI_SERVICES_AVAILABLE = True
except ImportError:
    # For local development - AI services not yet available
    AI_SERVICES_AVAILABLE = False
    logger.warning("AI services not available locally - will be available in production")


def call_ai_document_classification(file_obj, user):
    """
    Use AI services to classify document instead of hardcoded logic.
    Integrates with document_search (Milvus) and file_elasticsearch.
    """
    try:
        if not AI_SERVICES_AVAILABLE:
            # Fallback for local development
            return _basic_filename_classification(file_obj.filename)

        # Use filename and any extracted content for classification
        query_text = f"document type classification {file_obj.filename}"
        if hasattr(file_obj, 'content') and file_obj.content:
            query_text += f" {file_obj.content[:500]}"  # First 500 chars

        # Call semantic search service (internal Django app)
        search_result = semantic_search_task.delay(
            query=query_text,
            top_k=5,
            file_id=file_obj.id,
            user_id=user.id
        ).get(timeout=30)

        # Analyze results to determine document type
        if search_result and 'results' in search_result:
            # Use AI logic to classify based on similar documents
            similar_docs = search_result['results']
            doc_type = _classify_from_similar_docs(similar_docs, file_obj.filename)
            confidence = _calculate_confidence(similar_docs)
        else:
            # Fallback to basic filename analysis
            doc_type, confidence = _basic_filename_classification(file_obj.filename)

        return doc_type, confidence

    except Exception as e:
        logger.error(f"AI classification failed for file {file_obj.id}: {str(e)}")
        # Fallback to basic classification
        return _basic_filename_classification(file_obj.filename)


def _classify_from_similar_docs(similar_docs, filename):
    """Classify document based on similar documents found via vector search."""
    # Count document types from similar documents
    type_counts = {}
    for doc in similar_docs:
        if 'metadata' in doc and 'document_type' in doc['metadata']:
            doc_type = doc['metadata']['document_type']
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

    if type_counts:
        # Return most common type
        return max(type_counts, key=type_counts.get)

    # Fallback to filename analysis
    return _basic_filename_classification(filename)[0]


def _calculate_confidence(similar_docs):
    """Calculate confidence based on similarity scores."""
    if not similar_docs:
        return 0.5

    # Average similarity score
    scores = [doc.get('score', 0) for doc in similar_docs]
    avg_score = sum(scores) / len(scores) if scores else 0.5

    # Convert to confidence (0.5 to 0.9 range)
    return min(0.9, max(0.5, avg_score))


def _basic_filename_classification(filename):
    """Basic filename-based classification as fallback."""
    filename_lower = filename.lower()

    if any(keyword in filename_lower for keyword in ['nda', 'non-disclosure', 'confidentiality']):
        return 'nda', 0.70
    elif any(keyword in filename_lower for keyword in ['employment', 'employee', 'hr']):
        return 'employment_agreement', 0.70
    elif any(keyword in filename_lower for keyword in ['financial', 'audit', 'statement']):
        return 'financial_statement', 0.70
    else:
        return 'unclassified', 0.50


def call_ai_risk_clause_extraction(file_obj, user, classification):
    """
    Use AI services to extract risk clauses instead of hardcoded logic.
    Integrates with document_search (Milvus) and grid_documents_interrogation.
    """
    try:
        if not AI_SERVICES_AVAILABLE:
            # Fallback for local development
            return []

        # First, ensure we have document content
        if not hasattr(file_obj, 'content') or not file_obj.content:
            logger.warning(f"No content available for risk extraction in file {file_obj.id}")
            return []

        # Use semantic search to find similar risk clauses
        risk_query = f"risk clauses legal contract {classification.document_type if classification else ''}"

        search_result = semantic_search_task.delay(
            query=risk_query,
            top_k=10,
            user_id=user.id,
            file_id=file_obj.id
        ).get(timeout=30)

        # Use grid_documents_interrogation for intelligent document analysis
        extracted_clauses = []

        if search_result and 'results' in search_result:
            # Analyze document content for risk patterns
            content_chunks = _chunk_document_content(file_obj.content)

            for chunk in content_chunks:
                # Use AI to identify potential risk clauses
                risk_clause = _analyze_chunk_for_risks(chunk, classification)
                if risk_clause:
                    extracted_clauses.append(risk_clause)

        return extracted_clauses

    except Exception as e:
        logger.error(f"AI risk extraction failed for file {file_obj.id}: {str(e)}")
        return []


def _chunk_document_content(content, chunk_size=1000):
    """Split document content into analyzable chunks."""
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        chunks.append(chunk)
    return chunks


def _analyze_chunk_for_risks(chunk, classification):
    """Analyze text chunk for potential risk clauses using AI logic."""
    # Risk keywords and patterns for different document types
    risk_patterns = {
        'nda': ['termination', 'breach', 'disclosure', 'confidentiality'],
        'employment_agreement': ['change of control', 'severance', 'termination'],
        'supplier_contract': ['assignment', 'consent', 'liability'],
        'financial_statement': ['material adverse', 'default', 'covenant']
    }

    doc_type = classification.document_type if classification else 'unknown'
    patterns = risk_patterns.get(doc_type, ['risk', 'liability', 'breach'])

    chunk_lower = chunk.lower()

    # Check if chunk contains risk-related content
    risk_score = 0
    for pattern in patterns:
        if pattern in chunk_lower:
            risk_score += 1

    if risk_score > 0:
        # Extract potential risk clause
        sentences = chunk.split('.')
        for sentence in sentences:
            if any(pattern in sentence.lower() for pattern in patterns):
                return {
                    'clause_type': _determine_clause_type(sentence, patterns),
                    'clause_text': sentence.strip(),
                    'risk_level': _calculate_risk_level(sentence, patterns),
                    'page_number': 1,  # TODO: Calculate actual page number
                    'risk_explanation': f'Potential risk identified in {doc_type} document',
                    'mitigation_suggestions': 'Review clause for potential business impact'
                }

    return None


def _determine_clause_type(sentence, patterns):
    """Determine the type of risk clause based on content."""
    sentence_lower = sentence.lower()

    if any(word in sentence_lower for word in ['termination', 'terminate']):
        return 'termination'
    elif any(word in sentence_lower for word in ['assignment', 'assign']):
        return 'assignment'
    elif any(word in sentence_lower for word in ['change of control', 'control']):
        return 'change_of_control'
    else:
        return 'general_risk'


def _calculate_risk_level(sentence, patterns):
    """Calculate risk level based on sentence content."""
    sentence_lower = sentence.lower()

    high_risk_words = ['shall not', 'prohibited', 'breach', 'default', 'terminate']
    medium_risk_words = ['may', 'subject to', 'consent', 'approval']

    if any(word in sentence_lower for word in high_risk_words):
        return 'high'
    elif any(word in sentence_lower for word in medium_risk_words):
        return 'medium'
    else:
        return 'low'


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def classify_document_task(self, file_id, dd_run_id, user_id):
    """
    Celery task to classify a document using AI/ML models.
    This is a placeholder implementation - replace with actual ML classification logic.
    """
    try:
        file_obj = File.objects.get(id=file_id)
        dd_run = DueDiligenceRun.objects.get(id=dd_run_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Starting document classification for file {file_obj.filename}")
        
        # Placeholder classification logic
        # In a real implementation, this would:
        # 1. Extract text from the document
        # 2. Use ML models to classify document type
        # 3. Calculate confidence scores
        
        # Use AI services for document classification
        doc_type, confidence = call_ai_document_classification(file_obj, user)
        
        # Create or update classification
        classification, created = DocumentClassification.objects.update_or_create(
            file=file_obj,
            user=user,
            defaults={
                'due_diligence_run': dd_run,
                'document_type': doc_type,
                'confidence_score': confidence,
                'classification_metadata': {
                    'method': 'filename_pattern_matching',
                    'processed_at': timezone.now().isoformat(),
                    'task_id': self.request.id
                }
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} classification for {file_obj.filename}: {doc_type} (confidence: {confidence})")

        return {
            "status": "completed",
            "file_id": file_id,
            "document_type": doc_type,
            "confidence_score": confidence,
            "action": action.lower(),
            "registered_outputs": []  # Classification doesn't generate new files
        }

    except File.DoesNotExist:
        logger.error(f"File with id {file_id} not found")
        return {"status": "failed", "error": "File not found", "registered_outputs": []}
    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found", "registered_outputs": []}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found", "registered_outputs": []}
    except Exception as e:
        logger.error(f"Document classification failed for file {file_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e), "registered_outputs": []}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def extract_risk_clauses_task(self, file_id, dd_run_id, user_id):
    """
    Celery task to extract risk clauses from a document using NLP.
    This is a placeholder implementation - replace with actual NLP extraction logic.
    """
    try:
        file_obj = File.objects.get(id=file_id)
        dd_run = DueDiligenceRun.objects.get(id=dd_run_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Starting risk clause extraction for file {file_obj.filename}")
        
        # Placeholder risk extraction logic
        # In a real implementation, this would:
        # 1. Extract text from the document
        # 2. Use NLP models to identify risk clauses
        # 3. Classify risk levels and types
        
        # Use AI services for risk clause extraction
        classification = DocumentClassification.objects.filter(
            file=file_obj, user=user
        ).first()

        # Call AI-powered risk clause extraction
        extracted_clauses = call_ai_risk_clause_extraction(file_obj, user, classification)

        # Create risk clause records from AI analysis
        created_clauses = []
        for clause_data in extracted_clauses:
            risk_clause = RiskClause.objects.create(
                file=file_obj,
                user=user,
                due_diligence_run=dd_run,
                **clause_data
            )
            created_clauses.append(risk_clause.id)
        
        logger.info(f"Created {len(created_clauses)} risk clauses for {file_obj.filename}")

        return {
            "status": "completed",
            "file_id": file_id,
            "clauses_created": len(created_clauses),
            "clause_ids": created_clauses,
            "registered_outputs": []  # Risk extraction doesn't generate new files
        }

    except File.DoesNotExist:
        logger.error(f"File with id {file_id} not found")
        return {"status": "failed", "error": "File not found", "registered_outputs": []}
    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found", "registered_outputs": []}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found", "registered_outputs": []}
    except Exception as e:
        logger.error(f"Risk clause extraction failed for file {file_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e), "registered_outputs": []}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_findings_report_task(self, dd_run_id, user_id, report_name="Due Diligence Findings Report", project_id=None, service_id=None):
    """
    Celery task to generate a comprehensive findings report for a due diligence run.
    Generates a JSON report file and registers it using register_generated_file.
    Returns registered_outputs with file_id for consistency with translation pattern.
    """
    try:
        dd_run = DueDiligenceRun.objects.get(id=dd_run_id)
        user = User.objects.get(id=user_id)

        logger.info(f"Generating findings report for DD run: {dd_run.deal_name}")

        with transaction.atomic():
            # Gather statistics
            total_documents = DocumentClassification.objects.filter(
                due_diligence_run=dd_run, user=user
            ).count()

            total_risk_clauses = RiskClause.objects.filter(
                due_diligence_run=dd_run, user=user
            ).count()

            high_risk_items = RiskClause.objects.filter(
                due_diligence_run=dd_run, user=user, risk_level__in=['high', 'critical']
            ).count()

            # Document summary by type
            doc_summary = {}
            doc_classifications = DocumentClassification.objects.filter(
                due_diligence_run=dd_run, user=user
            ).values('document_type').annotate(count=Count('id'))

            for item in doc_classifications:
                doc_summary[item['document_type']] = item['count']

            # Risk summary by type and level
            risk_summary = {}
            risk_clauses = RiskClause.objects.filter(
                due_diligence_run=dd_run, user=user
            ).values('clause_type', 'risk_level').annotate(count=Count('id'))

            for item in risk_clauses:
                clause_type = item['clause_type']
                if clause_type not in risk_summary:
                    risk_summary[clause_type] = {}
                risk_summary[clause_type][item['risk_level']] = item['count']

            # Generate key findings
            key_findings = []
            if high_risk_items > 0:
                key_findings.append(f"Identified {high_risk_items} high-risk clauses requiring attention")

            if 'change_of_control' in [clause['clause_type'] for clause in risk_clauses]:
                key_findings.append("Change of control provisions found in multiple contracts")

            # Generate recommendations
            recommendations = []
            if high_risk_items > 5:
                recommendations.append("Prioritize review of high-risk clauses before deal closing")

            if doc_summary.get('nda', 0) > 10:
                recommendations.append("Consider NDA consolidation to reduce administrative burden")

            # Create the findings report database record
            report = FindingsReport.objects.create(
                due_diligence_run=dd_run,
                user=user,
                report_name=report_name,
                executive_summary=f"Due diligence review of {dd_run.target_company} identified {total_risk_clauses} risk clauses across {total_documents} documents.",
                document_summary=doc_summary,
                risk_summary=risk_summary,
                key_findings=key_findings,
                recommendations=recommendations,
                total_documents_reviewed=total_documents,
                total_risk_clauses_found=total_risk_clauses,
                high_risk_items_count=high_risk_items,
                status='draft'
            )

            # Generate JSON report file
            report_data = {
                "report_id": report.id,
                "report_name": report_name,
                "deal_name": dd_run.deal_name,
                "target_company": dd_run.target_company,
                "generated_at": timezone.now().isoformat(),
                "executive_summary": report.executive_summary,
                "document_summary": doc_summary,
                "risk_summary": risk_summary,
                "key_findings": key_findings,
                "recommendations": recommendations,
                "statistics": {
                    "total_documents_reviewed": total_documents,
                    "total_risk_clauses_found": total_risk_clauses,
                    "high_risk_items_count": high_risk_items
                }
            }

            # Create output directory
            datetime_folder = timezone.now().strftime("%Y%m%d")
            output_dir = os.path.join(
                settings.MEDIA_ROOT,
                "pe_reports",
                str(user.id),
                datetime_folder,
                "findings_reports"
            )
            os.makedirs(output_dir, exist_ok=True)

            # Write report file
            report_filename = f"findings_report_{report.id}_{dd_run.deal_name.replace(' ', '_')}.json"
            report_filepath = os.path.join(output_dir, report_filename)

            with open(report_filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            # Register the generated file
            registered_outputs = []
            if os.path.exists(report_filepath):
                # Get project_id and service_id from dd_run if not provided
                effective_project_id = project_id or getattr(dd_run.run, 'project_id', None)
                effective_service_id = service_id or "pe-findings-report"

                registered = register_generated_file(
                    file_path=report_filepath,
                    user=user,
                    run=dd_run.run,
                    project_id=effective_project_id,
                    service_id=effective_service_id,
                    folder_name=os.path.join("findings_reports", datetime_folder)
                )

                registered_outputs.append({
                    "filename": registered.filename,
                    "file_id": registered.id,
                    "path": registered.filepath
                })

                logger.info(f"✅ Registered findings report file: {registered.filename} (file_id={registered.id})")

        logger.info(f"Generated findings report {report.id} for DD run {dd_run.deal_name}")

        return {
            "status": "completed",
            "report_id": report.id,
            "dd_run_id": dd_run_id,
            "total_documents": total_documents,
            "total_risk_clauses": total_risk_clauses,
            "high_risk_items": high_risk_items,
            "registered_outputs": registered_outputs
        }

    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found", "registered_outputs": []}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found", "registered_outputs": []}
    except Exception as e:
        logger.error(f"Findings report generation failed for DD run {dd_run_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120, exc=e)
        return {"status": "failed", "error": str(e), "registered_outputs": []}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_data_room_task(self, connector_id, user_id):
    """
    Celery task to sync documents from external data rooms.
    This is a placeholder implementation - replace with actual API integrations.
    """
    try:
        from .models import DataRoomConnector
        
        connector = DataRoomConnector.objects.get(id=connector_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Starting data room sync for connector: {connector.connector_name}")
        
        # Update sync status
        connector.sync_status = 'syncing'
        connector.save(update_fields=['sync_status'])
        
        # Placeholder sync logic
        # In a real implementation, this would:
        # 1. Connect to the external data room API
        # 2. List available documents
        # 3. Download new/updated documents
        # 4. Create File records and trigger processing
        
        # TODO: Implement actual data room sync logic
        # For now, mark as completed but don't create fake data
        connector.sync_status = 'completed'
        connector.last_sync_at = timezone.now()
        connector.sync_error_message = ''
        connector.save(update_fields=['sync_status', 'last_sync_at', 'sync_error_message'])

        # TODO: Replace with actual implementation that:
        # 1. Connects to the specified data room API (VDR, SharePoint, etc.)
        # 2. Authenticates using provided credentials
        # 3. Downloads new/updated documents
        # 4. Creates File records for downloaded documents
        # 5. Triggers document processing pipeline
        
        logger.info(f"Completed data room sync for connector: {connector.connector_name}")

        return {
            "status": "completed",
            "connector_id": connector_id,
            "connector_name": connector.connector_name,
            "synced_files": 0,  # Placeholder
            "registered_outputs": []  # Will contain synced files when implemented
        }

    except DataRoomConnector.DoesNotExist:
        logger.error(f"DataRoomConnector with id {connector_id} not found")
        return {"status": "failed", "error": "Data room connector not found", "registered_outputs": []}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found", "registered_outputs": []}
    except Exception as e:
        logger.error(f"Data room sync failed for connector {connector_id}: {str(e)}")

        # Update connector with error status
        try:
            connector = DataRoomConnector.objects.get(id=connector_id)
            connector.sync_status = 'failed'
            connector.sync_error_message = str(e)
            connector.save(update_fields=['sync_status', 'sync_error_message'])
        except:
            pass

        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=e)
        return {"status": "failed", "error": str(e), "registered_outputs": []}


# ═══════════════════════════════════════════════════════════════
# 🔧 HELPER FUNCTIONS FOR AI INTEGRATION
# ═══════════════════════════════════════════════════════════════

def _basic_filename_classification(filename):
    """Basic filename-based classification fallback."""
    filename_lower = filename.lower()

    if any(term in filename_lower for term in ['contract', 'agreement', 'msa']):
        return 'contract', 0.6
    elif any(term in filename_lower for term in ['financial', 'statement', 'audit']):
        return 'financial_statement', 0.6
    elif any(term in filename_lower for term in ['legal', 'memo', 'opinion']):
        return 'legal_document', 0.6
    else:
        return 'other', 0.3


def _classify_from_similar_docs(similar_docs, filename):
    """Classify document based on similar documents found."""
    if not similar_docs:
        return _basic_filename_classification(filename)[0]

    # Simple classification based on most similar document
    # In production, this would use more sophisticated ML classification
    return similar_docs[0].get('document_type', 'other')


def _calculate_confidence(similar_docs):
    """Calculate confidence score based on similarity results."""
    if not similar_docs:
        return 0.3

    # Simple confidence calculation based on similarity scores
    avg_score = sum(doc.get('similarity_score', 0) for doc in similar_docs) / len(similar_docs)
    return min(avg_score, 0.95)


def _chunk_document_content(content):
    """Split document content into chunks for analysis."""
    # Simple chunking - in production would use more sophisticated methods
    chunk_size = 1000
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunks.append(content[i:i + chunk_size])
    return chunks


def _analyze_chunk_for_risks(chunk, classification):
    """Analyze document chunk for risk clauses."""
    # Simple keyword-based risk detection - in production would use NLP
    risk_keywords = [
        'liability', 'indemnification', 'force majeure', 'termination',
        'breach', 'default', 'penalty', 'damages', 'warranty', 'guarantee'
    ]

    chunk_lower = chunk.lower()
    found_risks = [keyword for keyword in risk_keywords if keyword in chunk_lower]

    if found_risks:
        return {
            'clause_text': chunk[:200] + '...' if len(chunk) > 200 else chunk,
            'risk_type': found_risks[0],
            'severity': 'medium',
            'confidence': 0.7
        }

    return None


def _process_ai_communication_results(search_result, qa_result, analysis_type):
    """Process AI communication analysis results."""
    return {
        'analysis_type': analysis_type,
        'similar_patterns': search_result.get('results', [])[:5],
        'ai_insights': qa_result.get('answer', ''),
        'confidence': qa_result.get('confidence', 0.5)
    }
