"""
Utility functions for the Class Actions application.
"""
import re
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from django.contrib.auth import get_user_model
from difflib import SequenceMatcher
from .models import IntakeForm, EvidenceDocument, MassClaimsRun

logger = logging.getLogger(__name__)
User = get_user_model()


def calculate_similarity_score(text1: str, text2: str) -> float:
    """
    Calculate similarity score between two text strings using SequenceMatcher.
    Returns a float between 0.0 and 1.0.
    """
    if not text1 or not text2:
        return 0.0
    
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def normalize_claimant_data(claimant_data: Dict) -> Dict:
    """
    Normalize claimant data for consistent comparison and duplicate detection.
    """
    normalized = {}
    
    # Normalize names
    first_name = claimant_data.get('first_name', '').strip().lower()
    last_name = claimant_data.get('last_name', '').strip().lower()
    normalized['first_name'] = first_name
    normalized['last_name'] = last_name
    normalized['full_name'] = f"{first_name} {last_name}".strip()
    
    # Normalize email
    email = claimant_data.get('email', '').strip().lower()
    normalized['email'] = email
    
    # Normalize phone (remove formatting)
    phone = claimant_data.get('phone', '')
    normalized_phone = re.sub(r'[^\d]', '', phone)
    normalized['phone'] = normalized_phone
    
    # Normalize address
    address = claimant_data.get('address', '').strip().lower()
    # Remove common abbreviations and normalize
    address = re.sub(r'\bst\b', 'street', address)
    address = re.sub(r'\bave\b', 'avenue', address)
    address = re.sub(r'\brd\b', 'road', address)
    address = re.sub(r'\bdr\b', 'drive', address)
    normalized['address'] = address
    
    return normalized


def detect_duplicate_claimants(form1: IntakeForm, form2: IntakeForm) -> Tuple[bool, float, str]:
    """
    Detect if two intake forms represent duplicate claimants.
    Returns (is_duplicate, similarity_score, reason).
    """
    data1 = normalize_claimant_data(form1.claimant_data)
    data2 = normalize_claimant_data(form2.claimant_data)
    
    # Exact email match (highest confidence)
    if data1['email'] and data2['email'] and data1['email'] == data2['email']:
        return True, 1.0, "Exact email match"
    
    # Exact phone match
    if data1['phone'] and data2['phone'] and len(data1['phone']) >= 10 and data1['phone'] == data2['phone']:
        return True, 0.95, "Exact phone match"
    
    # Name and address similarity
    name_similarity = calculate_similarity_score(data1['full_name'], data2['full_name'])
    address_similarity = calculate_similarity_score(data1['address'], data2['address'])
    
    # High name similarity with some address similarity
    if name_similarity >= 0.9 and address_similarity >= 0.7:
        combined_score = (name_similarity + address_similarity) / 2
        return True, combined_score, f"High name similarity ({name_similarity:.2f}) with address match ({address_similarity:.2f})"
    
    # Exact name match with different address (possible move)
    if name_similarity >= 0.95:
        return True, name_similarity, f"Exact name match ({name_similarity:.2f})"
    
    return False, max(name_similarity, address_similarity), "No significant similarity"


def generate_claimant_hash(claimant_data: Dict) -> str:
    """
    Generate a hash for claimant data to help with duplicate detection.
    """
    normalized = normalize_claimant_data(claimant_data)
    
    # Create a string from key identifying information
    hash_string = f"{normalized['email']}|{normalized['phone']}|{normalized['full_name']}"
    
    return hashlib.md5(hash_string.encode()).hexdigest()


def validate_intake_form_data(claimant_data: Dict) -> List[str]:
    """
    Validate intake form data and return list of validation errors.
    """
    errors = []
    
    # Required fields
    required_fields = {
        'first_name': 'First name',
        'last_name': 'Last name',
        'email': 'Email address',
        'phone': 'Phone number'
    }
    
    for field, display_name in required_fields.items():
        if not claimant_data.get(field, '').strip():
            errors.append(f"{display_name} is required")
    
    # Email validation
    email = claimant_data.get('email', '')
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append("Invalid email format")
    
    # Phone validation
    phone = claimant_data.get('phone', '')
    if phone:
        normalized_phone = re.sub(r'[^\d]', '', phone)
        if len(normalized_phone) < 10:
            errors.append("Phone number must be at least 10 digits")
    
    # Date validation (if birth_date provided)
    birth_date = claimant_data.get('birth_date')
    if birth_date:
        try:
            from datetime import datetime
            datetime.strptime(birth_date, '%Y-%m-%d')
        except ValueError:
            errors.append("Invalid birth date format (use YYYY-MM-DD)")
    
    return errors


def extract_pii_patterns(text: str) -> List[Dict]:
    """
    Extract PII patterns from text using regex patterns.
    This is a basic implementation - in production, use specialized NLP models.
    """
    pii_patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b',
    }
    
    found_pii = []
    
    for pii_type, pattern in pii_patterns.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            found_pii.append({
                'pii_type': pii_type,
                'original_text': match.group(),
                'start_position': match.start(),
                'end_position': match.end(),
                'confidence_score': 0.8  # Basic pattern matching confidence
            })
    
    return found_pii


def redact_pii_in_text(text: str, pii_instances: List[Dict]) -> str:
    """
    Redact PII instances in text, replacing with redaction markers.
    """
    # Sort PII instances by position (reverse order to maintain positions)
    sorted_pii = sorted(pii_instances, key=lambda x: x['start_position'], reverse=True)
    
    redacted_text = text
    
    for pii in sorted_pii:
        start = pii['start_position']
        end = pii['end_position']
        pii_type = pii['pii_type'].upper()
        
        redaction_marker = f"[{pii_type} REDACTED]"
        redacted_text = redacted_text[:start] + redaction_marker + redacted_text[end:]
    
    return redacted_text


def calculate_evidence_relevance_score(file_name: str, content: str, case_keywords: List[str]) -> float:
    """
    Calculate relevance score for evidence documents based on content and keywords.
    """
    score = 0.0
    
    # Base score from filename
    filename_lower = file_name.lower()
    
    # File type scoring
    if any(ext in filename_lower for ext in ['.pdf', '.doc', '.docx']):
        score += 0.2
    elif any(ext in filename_lower for ext in ['.eml', '.msg']):
        score += 0.3  # Emails often more relevant
    
    # Keyword matching in filename
    filename_matches = sum(1 for keyword in case_keywords if keyword.lower() in filename_lower)
    score += min(0.3, filename_matches * 0.1)
    
    # Content analysis (if available)
    if content:
        content_lower = content.lower()
        content_matches = sum(1 for keyword in case_keywords if keyword.lower() in content_lower)
        score += min(0.5, content_matches * 0.05)
    
    return min(1.0, score)


def generate_bates_numbers(prefix: str, start_num: int, count: int) -> List[str]:
    """
    Generate sequential Bates numbers with given prefix.
    """
    bates_numbers = []
    
    for i in range(count):
        bates_num = f"{prefix}{start_num + i:06d}"
        bates_numbers.append(bates_num)
    
    return bates_numbers


def calculate_settlement_distribution(total_amount: float, approved_claims: int, 
                                    attorney_fees_pct: float = 0.25, 
                                    admin_costs_pct: float = 0.05) -> Dict:
    """
    Calculate settlement distribution amounts.
    """
    attorney_fees = total_amount * attorney_fees_pct
    admin_costs = total_amount * admin_costs_pct
    net_settlement_fund = total_amount - attorney_fees - admin_costs
    
    per_claimant_amount = net_settlement_fund / approved_claims if approved_claims > 0 else 0
    
    return {
        'total_settlement_amount': total_amount,
        'attorney_fees': attorney_fees,
        'administration_costs': admin_costs,
        'net_settlement_fund': net_settlement_fund,
        'approved_claims_count': approved_claims,
        'per_claimant_amount': per_claimant_amount
    }


def generate_case_summary(mc_run: MassClaimsRun) -> Dict:
    """
    Generate comprehensive summary for a mass claims run.
    """
    # Get intake form statistics
    intake_forms = IntakeForm.objects.filter(mass_claims_run=mc_run)
    total_forms = intake_forms.count()
    approved_forms = intake_forms.filter(processing_status='approved').count()
    duplicate_forms = intake_forms.filter(is_duplicate=True).count()
    
    # Get evidence document statistics
    evidence_docs = EvidenceDocument.objects.filter(mass_claims_run=mc_run)
    total_evidence = evidence_docs.count()
    culled_evidence = evidence_docs.filter(is_culled=True).count()
    pii_documents = evidence_docs.filter(contains_pii=True).count()
    
    # Calculate approval rate
    approval_rate = (approved_forms / total_forms * 100) if total_forms > 0 else 0
    
    # Calculate duplicate rate
    duplicate_rate = (duplicate_forms / total_forms * 100) if total_forms > 0 else 0
    
    # Calculate culling rate
    culling_rate = (culled_evidence / total_evidence * 100) if total_evidence > 0 else 0
    
    return {
        'case_name': mc_run.case_name,
        'case_number': mc_run.case_number,
        'case_type': mc_run.get_case_type_display(),
        'status': mc_run.get_status_display(),
        'intake_forms': {
            'total': total_forms,
            'approved': approved_forms,
            'duplicates': duplicate_forms,
            'approval_rate': round(approval_rate, 2),
            'duplicate_rate': round(duplicate_rate, 2)
        },
        'evidence_documents': {
            'total': total_evidence,
            'culled': culled_evidence,
            'with_pii': pii_documents,
            'culling_rate': round(culling_rate, 2)
        },
        'settlement_amount': float(mc_run.settlement_amount) if mc_run.settlement_amount else None,
        'claim_deadline': mc_run.claim_deadline.isoformat() if mc_run.claim_deadline else None
    }


def export_claimant_data(mc_run: MassClaimsRun, format_type: str = 'csv') -> str:
    """
    Export claimant data in specified format.
    Returns the file path or content string.
    """
    intake_forms = IntakeForm.objects.filter(
        mass_claims_run=mc_run,
        processing_status='approved',
        is_duplicate=False
    )
    
    if format_type.lower() == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Claimant ID', 'First Name', 'Last Name', 'Email', 'Phone',
            'Address', 'Submitted Date', 'Status'
        ])
        
        # Write data
        for form in intake_forms:
            data = form.claimant_data
            writer.writerow([
                str(form.claimant_id),
                data.get('first_name', ''),
                data.get('last_name', ''),
                data.get('email', ''),
                data.get('phone', ''),
                data.get('address', ''),
                form.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
                form.get_processing_status_display()
            ])
        
        return output.getvalue()
    
    else:
        raise ValueError(f"Unsupported export format: {format_type}")


def validate_settlement_data(settlement_data: Dict) -> List[str]:
    """
    Validate settlement tracking data.
    """
    errors = []
    
    # Required fields
    if not settlement_data.get('total_settlement_amount'):
        errors.append("Total settlement amount is required")
    
    # Validate amounts are positive
    amount_fields = ['total_settlement_amount', 'attorney_fees', 'administration_costs']
    for field in amount_fields:
        value = settlement_data.get(field)
        if value is not None and value < 0:
            errors.append(f"{field.replace('_', ' ').title()} must be positive")
    
    # Validate dates
    date_fields = ['notice_deadline', 'objection_deadline', 'opt_out_deadline']
    for field in date_fields:
        date_value = settlement_data.get(field)
        if date_value:
            try:
                from datetime import datetime
                if isinstance(date_value, str):
                    datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"Invalid {field.replace('_', ' ')} format")
    
    return errors
