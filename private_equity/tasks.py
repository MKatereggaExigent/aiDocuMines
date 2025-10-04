from celery import shared_task
import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from core.models import File
from .models import (
    DueDiligenceRun, DocumentClassification, RiskClause, FindingsReport
)

logger = logging.getLogger(__name__)
User = get_user_model()


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
        
        # Mock classification based on filename patterns
        filename_lower = file_obj.filename.lower()
        
        if 'nda' in filename_lower or 'non-disclosure' in filename_lower:
            doc_type = 'nda'
            confidence = 0.95
        elif 'employment' in filename_lower or 'employee' in filename_lower:
            doc_type = 'employment_agreement'
            confidence = 0.88
        elif 'lease' in filename_lower or 'rental' in filename_lower:
            doc_type = 'lease_agreement'
            confidence = 0.92
        elif 'supplier' in filename_lower or 'vendor' in filename_lower:
            doc_type = 'supplier_contract'
            confidence = 0.85
        elif 'privacy' in filename_lower or 'data' in filename_lower:
            doc_type = 'privacy_policy'
            confidence = 0.78
        elif 'ip' in filename_lower or 'patent' in filename_lower or 'trademark' in filename_lower:
            doc_type = 'ip_document'
            confidence = 0.82
        else:
            doc_type = 'other'
            confidence = 0.60
        
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
            "action": action.lower()
        }
        
    except File.DoesNotExist:
        logger.error(f"File with id {file_id} not found")
        return {"status": "failed", "error": "File not found"}
    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Document classification failed for file {file_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e)}


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
        
        # Mock risk clauses based on document type
        classification = DocumentClassification.objects.filter(
            file=file_obj, user=user
        ).first()
        
        mock_clauses = []
        
        if classification and classification.document_type == 'nda':
            mock_clauses = [
                {
                    'clause_type': 'termination',
                    'clause_text': 'This agreement shall terminate upon change of control of either party.',
                    'risk_level': 'high',
                    'page_number': 2,
                    'risk_explanation': 'Change of control termination could affect deal continuity.',
                    'mitigation_suggestions': 'Negotiate carve-out for planned transactions.'
                }
            ]
        elif classification and classification.document_type == 'employment_agreement':
            mock_clauses = [
                {
                    'clause_type': 'change_of_control',
                    'clause_text': 'Employee entitled to severance upon change of control.',
                    'risk_level': 'medium',
                    'page_number': 3,
                    'risk_explanation': 'Change of control provisions increase transaction costs.',
                    'mitigation_suggestions': 'Calculate total severance exposure across all employees.'
                }
            ]
        elif classification and classification.document_type == 'supplier_contract':
            mock_clauses = [
                {
                    'clause_type': 'assignment',
                    'clause_text': 'Contract may not be assigned without supplier consent.',
                    'risk_level': 'high',
                    'page_number': 1,
                    'risk_explanation': 'Assignment restrictions could prevent deal completion.',
                    'mitigation_suggestions': 'Obtain supplier consent prior to closing.'
                }
            ]
        
        # Create risk clause records
        created_clauses = []
        for clause_data in mock_clauses:
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
            "clause_ids": created_clauses
        }
        
    except File.DoesNotExist:
        logger.error(f"File with id {file_id} not found")
        return {"status": "failed", "error": "File not found"}
    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Risk clause extraction failed for file {file_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_findings_report_task(self, dd_run_id, user_id, report_name="Due Diligence Findings Report"):
    """
    Celery task to generate a comprehensive findings report for a due diligence run.
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
            
            # Create the findings report
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
        
        logger.info(f"Generated findings report {report.id} for DD run {dd_run.deal_name}")
        
        return {
            "status": "completed",
            "report_id": report.id,
            "dd_run_id": dd_run_id,
            "total_documents": total_documents,
            "total_risk_clauses": total_risk_clauses,
            "high_risk_items": high_risk_items
        }
        
    except DueDiligenceRun.DoesNotExist:
        logger.error(f"DueDiligenceRun with id {dd_run_id} not found")
        return {"status": "failed", "error": "Due diligence run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Findings report generation failed for DD run {dd_run_id}: {str(e)}")
        # Retry the task if it hasn't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120, exc=e)
        return {"status": "failed", "error": str(e)}


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
        
        # Mock successful sync
        connector.sync_status = 'completed'
        connector.last_sync_at = timezone.now()
        connector.sync_error_message = ''
        connector.save(update_fields=['sync_status', 'last_sync_at', 'sync_error_message'])
        
        logger.info(f"Completed data room sync for connector: {connector.connector_name}")
        
        return {
            "status": "completed",
            "connector_id": connector_id,
            "connector_name": connector.connector_name,
            "synced_files": 0  # Placeholder
        }
        
    except DataRoomConnector.DoesNotExist:
        logger.error(f"DataRoomConnector with id {connector_id} not found")
        return {"status": "failed", "error": "Data room connector not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
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
        return {"status": "failed", "error": str(e)}
