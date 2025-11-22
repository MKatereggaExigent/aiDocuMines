"""
DSPy signatures for Class Actions LLM processing.
Defines structured LLM interactions for mass claims and class action litigation.
"""
import dspy
from typing import List, Optional


# ============================================================================
# Document Classification Signature
# ============================================================================

class ClassifyCADocument(dspy.Signature):
    """
    Classify a document in the context of class action litigation.
    Identify document type, evidence relevance, and PII presence.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the document to classify")
    case_name = dspy.InputField(desc="Name of the class action case", default="")
    case_type = dspy.InputField(desc="Type of class action (e.g., 'consumer_protection', 'securities')", default="consumer_protection")
    
    # Outputs
    document_type = dspy.OutputField(desc="Type of document (e.g., 'intake_form', 'evidence_email', 'financial_record')")
    evidence_type = dspy.OutputField(desc="Specific evidence type if applicable")
    relevance = dspy.OutputField(desc="Relevance to case: highly_relevant, relevant, marginally_relevant, or not_relevant")
    relevance_score = dspy.OutputField(desc="Relevance score between 0.0 and 1.0")
    contains_pii = dspy.OutputField(desc="Whether document contains PII (true/false)")
    privilege_status = dspy.OutputField(desc="Privilege status: none, attorney_client, work_product, or other")
    recommended_action = dspy.OutputField(desc="Recommended next action for this document")
    confidence_score = dspy.OutputField(desc="Classification confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of the classification")


# ============================================================================
# PII Detection Signature
# ============================================================================

class DetectPII(dspy.Signature):
    """
    Detect and identify personally identifiable information (PII) in documents.
    Extract PII instances with location and confidence scores.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the document to analyze")
    case_name = dspy.InputField(desc="Name of the class action case", default="")
    pii_types_to_detect = dspy.InputField(desc="Specific PII types to detect (comma-separated)", default="all")
    
    # Outputs
    pii_instances_json = dspy.OutputField(desc="JSON array of PII instances, each with: pii_type, original_text, redacted_text, page_number, position_start, position_end, confidence_score")
    total_pii_found = dspy.OutputField(desc="Total number of PII instances found")
    requires_redaction = dspy.OutputField(desc="Whether redaction is required (true/false)")
    redaction_summary = dspy.OutputField(desc="Summary of redaction needs")
    confidence_score = dspy.OutputField(desc="Overall detection confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of PII detection results")


# ============================================================================
# Evidence Culling Signature
# ============================================================================

class CullEvidence(dspy.Signature):
    """
    Analyze evidence documents for relevance and determine if they should be culled.
    Assess relevance to case issues and identify key topics.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the evidence document")
    case_name = dspy.InputField(desc="Name of the class action case")
    case_type = dspy.InputField(desc="Type of class action case")
    key_issues = dspy.InputField(desc="Key issues in the case (comma-separated)", default="")
    date_range_start = dspy.InputField(desc="Start date for relevance", default="")
    date_range_end = dspy.InputField(desc="End date for relevance", default="")
    
    # Outputs
    relevance_score = dspy.OutputField(desc="Relevance score (0.0 to 1.0)")
    relevance_level = dspy.OutputField(desc="Relevance level: highly_relevant, relevant, marginally_relevant, or not_relevant")
    should_cull = dspy.OutputField(desc="Whether to cull this document (true/false)")
    cull_reason = dspy.OutputField(desc="Reason for culling if applicable")
    key_topics = dspy.OutputField(desc="Key topics found in document (comma-separated)")
    relevant_excerpts = dspy.OutputField(desc="Relevant text excerpts (pipe-separated)")
    confidence_score = dspy.OutputField(desc="Analysis confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of culling decision")


# ============================================================================
# Duplicate Detection Signature
# ============================================================================

class DetectDuplicateClaims(dspy.Signature):
    """
    Detect duplicate claimant submissions in mass claims processing.
    Compare claimant data against existing claims to identify duplicates.
    """
    # Inputs
    claimant_data_json = dspy.InputField(desc="JSON of current claimant data")
    existing_claims_json = dspy.InputField(desc="JSON array of existing claims to compare against")
    case_name = dspy.InputField(desc="Name of the class action case")
    
    # Outputs
    is_duplicate = dspy.OutputField(desc="Whether this is a duplicate (true/false)")
    duplicate_matches_json = dspy.OutputField(desc="JSON array of potential duplicates, each with: claimant_id, similarity_score, matching_fields, is_likely_duplicate")
    best_match_score = dspy.OutputField(desc="Highest similarity score (0.0 to 1.0)")
    recommendation = dspy.OutputField(desc="Recommendation on how to handle this claim")
    confidence_score = dspy.OutputField(desc="Detection confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of duplicate detection results")


# ============================================================================
# Intake Form Validation Signature
# ============================================================================

class ValidateIntakeForm(dspy.Signature):
    """
    Validate intake form submissions for completeness and accuracy.
    Check required fields, data quality, and eligibility criteria.
    """
    # Inputs
    claimant_data_json = dspy.InputField(desc="JSON of claimant form data")
    case_name = dspy.InputField(desc="Name of the class action case")
    required_fields = dspy.InputField(desc="Required fields (comma-separated)", default="")
    eligibility_criteria = dspy.InputField(desc="Eligibility criteria to check", default="")
    
    # Outputs
    is_valid = dspy.OutputField(desc="Whether the form is valid (true/false)")
    validation_errors_json = dspy.OutputField(desc="JSON array of validation errors")
    completeness_score = dspy.OutputField(desc="Form completeness score (0.0 to 1.0)")
    meets_eligibility = dspy.OutputField(desc="Whether claimant meets eligibility criteria (true/false)")
    recommended_status = dspy.OutputField(desc="Recommended processing status: approved, rejected, or needs_review")
    confidence_score = dspy.OutputField(desc="Validation confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of validation results")


# ============================================================================
# Settlement Analysis Signature
# ============================================================================

class AnalyzeSettlement(dspy.Signature):
    """
    Analyze settlement terms and calculate distribution recommendations.
    Assess fairness and provide distribution guidance.
    """
    # Inputs
    settlement_details_json = dspy.InputField(desc="JSON of settlement details")
    total_claims = dspy.InputField(desc="Total number of approved claims")
    case_name = dspy.InputField(desc="Name of the class action case")
    
    # Outputs
    fairness_assessment = dspy.OutputField(desc="Assessment of settlement fairness")
    distribution_recommendation = dspy.OutputField(desc="Recommended distribution approach")
    per_claim_estimate = dspy.OutputField(desc="Estimated amount per claim")
    potential_issues = dspy.OutputField(desc="Potential issues with the settlement")
    confidence_score = dspy.OutputField(desc="Analysis confidence (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of settlement analysis")

