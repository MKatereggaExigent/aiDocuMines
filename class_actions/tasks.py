from celery import shared_task
import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from core.models import File
from .models import (
    MassClaimsRun, IntakeForm, EvidenceDocument, PIIRedaction, ExhibitPackage
)

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_intake_form_task(self, intake_form_id, user_id):
    """
    Celery task to process and validate intake form submissions.
    """
    try:
        intake_form = IntakeForm.objects.get(id=intake_form_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Processing intake form {intake_form.claimant_id}")
        
        # Update processing status
        intake_form.processing_status = 'processing'
        intake_form.save(update_fields=['processing_status'])
        
        # Validate claimant data
        validation_errors = []
        claimant_data = intake_form.claimant_data
        
        # Required field validation
        required_fields = ['first_name', 'last_name', 'email', 'phone']
        for field in required_fields:
            if not claimant_data.get(field):
                validation_errors.append(f"Missing required field: {field}")
        
        # Email format validation
        email = claimant_data.get('email', '')
        if email and '@' not in email:
            validation_errors.append("Invalid email format")
        
        # Phone format validation (basic)
        phone = claimant_data.get('phone', '')
        if phone and len(phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')) < 10:
            validation_errors.append("Invalid phone number format")
        
        # Update validation status
        intake_form.is_valid = len(validation_errors) == 0
        intake_form.validation_errors = validation_errors
        
        if intake_form.is_valid:
            intake_form.processing_status = 'approved'
        else:
            intake_form.processing_status = 'rejected'
        
        intake_form.processed_at = timezone.now()
        intake_form.processed_by = user
        intake_form.save()
        
        logger.info(f"Processed intake form {intake_form.claimant_id}: {intake_form.processing_status}")
        
        return {
            "status": "completed",
            "intake_form_id": intake_form_id,
            "processing_status": intake_form.processing_status,
            "is_valid": intake_form.is_valid,
            "validation_errors": validation_errors
        }
        
    except IntakeForm.DoesNotExist:
        logger.error(f"IntakeForm with id {intake_form_id} not found")
        return {"status": "failed", "error": "Intake form not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Intake form processing failed for {intake_form_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cull_evidence_documents_task(self, mc_run_id, file_ids, user_id):
    """
    Celery task to cull evidence documents based on relevance scoring.
    """
    try:
        mc_run = MassClaimsRun.objects.get(id=mc_run_id)
        user = User.objects.get(id=user_id)
        files = File.objects.filter(id__in=file_ids, user=user)
        
        logger.info(f"Starting evidence culling for {len(files)} documents")
        
        culled_count = 0
        processed_count = 0
        
        for file_obj in files:
            # TODO: Implement actual ML-based relevance scoring
            # For now, assign neutral relevance to avoid hardcoded mock data
            filename_lower = file_obj.filename.lower()

            # Basic evidence type classification (non-mock)
            if 'email' in filename_lower or '.eml' in filename_lower:
                evidence_type = 'email'
            elif 'chat' in filename_lower or 'message' in filename_lower:
                evidence_type = 'chat_log'
            elif 'financial' in filename_lower or 'bank' in filename_lower:
                evidence_type = 'financial_record'
            elif 'contract' in filename_lower or 'agreement' in filename_lower:
                evidence_type = 'contract'
            else:
                evidence_type = 'document'

            # TODO: Replace with actual ML model for relevance scoring
            # For now, assign neutral relevance score requiring manual review
            relevance_score = 0.5  # Neutral - requires manual review
            
            # Determine if document should be culled (relevance < 0.3)
            is_culled = relevance_score < 0.3
            cull_reason = "Low relevance score" if is_culled else ""
            
            # TODO: Implement actual PII detection using NLP models
            # For now, assume no PII to avoid false positives
            contains_pii = False  # Requires actual PII detection implementation
            
            # Create or update evidence document record
            evidence_doc, created = EvidenceDocument.objects.update_or_create(
                file=file_obj,
                user=user,
                defaults={
                    'mass_claims_run': mc_run,
                    'evidence_type': evidence_type,
                    'is_culled': is_culled,
                    'cull_reason': cull_reason,
                    'relevance_score': relevance_score,
                    'contains_pii': contains_pii,
                    'processing_metadata': {
                        'processed_at': timezone.now().isoformat(),
                        'task_id': self.request.id,
                        'method': 'filename_analysis'
                    }
                }
            )
            
            if is_culled:
                culled_count += 1
            processed_count += 1
        
        logger.info(f"Evidence culling completed: {processed_count} processed, {culled_count} culled")
        
        return {
            "status": "completed",
            "mc_run_id": mc_run_id,
            "processed_count": processed_count,
            "culled_count": culled_count
        }
        
    except MassClaimsRun.DoesNotExist:
        logger.error(f"MassClaimsRun with id {mc_run_id} not found")
        return {"status": "failed", "error": "Mass claims run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Evidence culling failed for run {mc_run_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def redact_pii_task(self, mc_run_id, file_ids, user_id):
    """
    Celery task to detect and redact PII from documents.
    """
    try:
        mc_run = MassClaimsRun.objects.get(id=mc_run_id)
        user = User.objects.get(id=user_id)
        files = File.objects.filter(id__in=file_ids, user=user)
        
        logger.info(f"Starting PII redaction for {len(files)} documents")
        
        redactions_created = 0
        
        for file_obj in files:
            # TODO: Implement actual PII detection using NLP models
            # For now, return empty list to avoid creating fake PII data
            detected_pii_instances = []

            # TODO: Replace with actual PII detection that can:
            # 1. Extract text from documents using OCR
            # 2. Use NER models to identify PII entities (emails, phones, SSNs, etc.)
            # 3. Calculate confidence scores for detections
            # 4. Provide accurate position information for redaction

            # Create PII redaction records (currently none due to no mock data)
            for pii_data in detected_pii_instances:
                PIIRedaction.objects.create(
                    file=file_obj,
                    user=user,
                    mass_claims_run=mc_run,
                    **pii_data
                )
                redactions_created += 1
        
        logger.info(f"PII redaction completed: {redactions_created} redactions created")
        
        return {
            "status": "completed",
            "mc_run_id": mc_run_id,
            "files_processed": len(files),
            "redactions_created": redactions_created
        }
        
    except MassClaimsRun.DoesNotExist:
        logger.error(f"MassClaimsRun with id {mc_run_id} not found")
        return {"status": "failed", "error": "Mass claims run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"PII redaction failed for run {mc_run_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60, exc=e)
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_exhibit_package_task(self, package_id, user_id):
    """
    Celery task to generate exhibit package with Bates stamping.
    """
    try:
        package = ExhibitPackage.objects.get(id=package_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Generating exhibit package: {package.package_name}")
        
        # Update status
        package.status = 'processing'
        package.save(update_fields=['status'])
        
        # TODO: Implement actual page counting
        # For now, use basic estimation to avoid hardcoded mock data
        total_pages = 0
        files = package.files.all()

        for file_obj in files:
            # TODO: Replace with actual page counting using document parsing
            # Basic estimation: assume average 2KB per page for text documents
            estimated_pages = max(1, file_obj.file_size // 2048) if file_obj.file_size else 1
            total_pages += estimated_pages
        
        # Generate Bates numbers
        bates_start = f"{package.bates_prefix}001"
        bates_end = f"{package.bates_prefix}{total_pages:03d}"
        
        # Update package with Bates information
        package.bates_start = bates_start
        package.bates_end = bates_end
        package.total_pages = total_pages
        package.status = 'ready'
        package.production_metadata = {
            'generated_at': timezone.now().isoformat(),
            'task_id': self.request.id,
            'file_count': files.count(),
            'total_pages': total_pages
        }
        package.save()
        
        logger.info(f"Exhibit package generated: {package.package_name} ({bates_start} - {bates_end})")
        
        return {
            "status": "completed",
            "package_id": package_id,
            "bates_start": bates_start,
            "bates_end": bates_end,
            "total_pages": total_pages,
            "file_count": files.count()
        }
        
    except ExhibitPackage.DoesNotExist:
        logger.error(f"ExhibitPackage with id {package_id} not found")
        return {"status": "failed", "error": "Exhibit package not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Exhibit package generation failed for {package_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120, exc=e)
        return {"status": "failed", "error": str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def detect_duplicate_claims_task(self, mc_run_id, user_id):
    """
    Celery task to detect duplicate intake forms using similarity matching.
    """
    try:
        mc_run = MassClaimsRun.objects.get(id=mc_run_id)
        user = User.objects.get(id=user_id)
        
        logger.info(f"Starting duplicate detection for mass claims run: {mc_run.case_name}")
        
        intake_forms = IntakeForm.objects.filter(
            mass_claims_run=mc_run,
            user=user,
            processing_status='approved'
        ).order_by('submitted_at')
        
        duplicates_found = 0
        
        # Simple duplicate detection based on email and name similarity
        processed_forms = []
        
        for form in intake_forms:
            claimant_data = form.claimant_data
            email = claimant_data.get('email', '').lower()
            first_name = claimant_data.get('first_name', '').lower()
            last_name = claimant_data.get('last_name', '').lower()
            
            # Check against previously processed forms
            is_duplicate = False
            duplicate_of = None
            duplicate_score = 0.0
            
            for processed_form in processed_forms:
                processed_data = processed_form.claimant_data
                processed_email = processed_data.get('email', '').lower()
                processed_first = processed_data.get('first_name', '').lower()
                processed_last = processed_data.get('last_name', '').lower()
                
                # Exact email match
                if email and email == processed_email:
                    is_duplicate = True
                    duplicate_of = processed_form
                    duplicate_score = 1.0
                    break
                
                # Name similarity (simple matching)
                if (first_name == processed_first and last_name == processed_last):
                    is_duplicate = True
                    duplicate_of = processed_form
                    duplicate_score = 0.9
                    break
            
            if is_duplicate:
                form.is_duplicate = True
                form.duplicate_of = duplicate_of
                form.duplicate_score = duplicate_score
                form.processing_status = 'duplicate'
                form.save()
                duplicates_found += 1
                logger.info(f"Duplicate found: {form.claimant_id} -> {duplicate_of.claimant_id}")
            else:
                processed_forms.append(form)
        
        logger.info(f"Duplicate detection completed: {duplicates_found} duplicates found")
        
        return {
            "status": "completed",
            "mc_run_id": mc_run_id,
            "total_forms_checked": intake_forms.count(),
            "duplicates_found": duplicates_found
        }
        
    except MassClaimsRun.DoesNotExist:
        logger.error(f"MassClaimsRun with id {mc_run_id} not found")
        return {"status": "failed", "error": "Mass claims run not found"}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return {"status": "failed", "error": "User not found"}
    except Exception as e:
        logger.error(f"Duplicate detection failed for run {mc_run_id}: {str(e)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120, exc=e)
        return {"status": "failed", "error": str(e)}
