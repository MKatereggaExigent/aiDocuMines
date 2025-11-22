"""
DSPy signatures for Regulatory Compliance LLM processing.
Defines structured input/output interfaces for compliance analysis tasks.
"""

import dspy


class MapRegulatoryRequirement(dspy.Signature):
    """
    Map organizational policies to regulatory requirements.
    
    Analyzes policy documents to determine compliance with specific
    regulatory requirements and identifies gaps.
    """
    
    policy_text = dspy.InputField(desc="Organizational policy text to analyze")
    framework = dspy.InputField(desc="Regulatory framework (gdpr, ccpa, hipaa, etc.)")
    requirement_id = dspy.InputField(desc="Specific requirement ID to check (optional)")
    
    requirement_id = dspy.OutputField(desc="Regulatory requirement identifier")
    requirement_text = dspy.OutputField(desc="Full text of the regulatory requirement")
    requirement_category = dspy.OutputField(desc="Category of requirement (e.g., 'Data Protection', 'Access Control')")
    compliance_status = dspy.OutputField(desc="Compliance status (compliant, partial, non_compliant, not_applicable)")
    policy_sections = dspy.OutputField(desc="Comma-separated relevant policy sections")
    gap_analysis = dspy.OutputField(desc="Detailed analysis of compliance gaps")
    recommendations = dspy.OutputField(desc="Comma-separated recommendations for achieving compliance")
    confidence = dspy.OutputField(desc="Mapping confidence score (0.0 to 1.0)")


class ProcessDSAR(dspy.Signature):
    """
    Process Data Subject Access Requests (DSAR) for GDPR/CCPA compliance.
    
    Analyzes DSAR requests to classify type, identify data categories,
    and recommend fulfillment actions.
    """
    
    request_text = dspy.InputField(desc="Text of the DSAR request")
    request_type = dspy.InputField(desc="Type of request (access, rectification, erasure, etc.)")
    data_subject_info = dspy.InputField(desc="Information about the data subject (name, email, etc.)")
    
    classified_request_type = dspy.OutputField(desc="Classified request type (access, rectification, erasure, etc.)")
    data_categories_requested = dspy.OutputField(desc="Comma-separated data categories requested (personal_identifiable, financial, health, etc.)")
    systems_to_search = dspy.OutputField(desc="Comma-separated systems that need to be searched")
    estimated_scope = dspy.OutputField(desc="Estimated scope of the request (e.g., '50-100 records across 3 systems')")
    deadline = dspy.OutputField(desc="Regulatory deadline for response (YYYY-MM-DD format)")
    complexity_level = dspy.OutputField(desc="Complexity level (simple, moderate, complex)")
    recommended_actions = dspy.OutputField(desc="Comma-separated recommended actions to fulfill the request")
    risk_assessment = dspy.OutputField(desc="Risk assessment for this request")


class AnalyzeDataInventory(dspy.Signature):
    """
    Analyze data processing activities for privacy compliance.
    
    Creates data inventory entries by analyzing system descriptions
    and identifying data categories, purposes, and legal basis.
    """
    
    system_description = dspy.InputField(desc="Description of the system or process")
    data_flows = dspy.InputField(desc="Description of data flows (optional)")
    purpose = dspy.InputField(desc="Purpose of data processing")
    
    activity_name = dspy.OutputField(desc="Name of the processing activity")
    data_categories = dspy.OutputField(desc="Comma-separated data categories processed (personal_identifiable, sensitive, financial, etc.)")
    processing_purposes = dspy.OutputField(desc="Comma-separated purposes of processing")
    legal_basis = dspy.OutputField(desc="Legal basis for processing (consent, contract, legitimate interest, etc.)")
    data_sources = dspy.OutputField(desc="Comma-separated sources of data")
    data_recipients = dspy.OutputField(desc="Comma-separated recipients of data")
    retention_period = dspy.OutputField(desc="Data retention period")
    security_measures = dspy.OutputField(desc="Comma-separated security measures in place")
    cross_border_transfers = dspy.OutputField(desc="Whether data crosses borders (true/false)")
    risk_level = dspy.OutputField(desc="Overall risk level (critical, high, medium, low, info)")


class AnalyzeRedaction(dspy.Signature):
    """
    Analyze documents for required redactions under privacy regulations.
    
    Identifies sensitive information that must be redacted and applies
    redaction rules based on compliance framework.
    """
    
    document_text = dspy.InputField(desc="Document text to analyze for redaction")
    redaction_rules = dspy.InputField(desc="Comma-separated redaction rules to apply")
    framework = dspy.InputField(desc="Compliance framework (gdpr, ccpa, hipaa, etc.)")
    
    redaction_items_json = dspy.OutputField(desc="JSON array of items to redact: [{text, category, start_pos, end_pos, reason}]")
    redaction_categories = dspy.OutputField(desc="Comma-separated categories of information to redact")
    risk_if_not_redacted = dspy.OutputField(desc="Risk level if items not redacted (critical, high, medium, low)")
    redacted_text = dspy.OutputField(desc="Text with redactions applied (use [REDACTED: category] format)")
    redaction_summary = dspy.OutputField(desc="Summary of redactions made")


class GenerateComplianceAlert(dspy.Signature):
    """
    Generate compliance alerts for potential violations.
    
    Analyzes activities or findings to identify compliance violations
    and generate actionable alerts with remediation steps.
    """
    
    activity_description = dspy.InputField(desc="Description of the activity or finding")
    framework = dspy.InputField(desc="Relevant compliance framework (gdpr, ccpa, hipaa, etc.)")
    context = dspy.InputField(desc="Additional context (optional)")
    
    alert_type = dspy.OutputField(desc="Type of compliance alert (e.g., 'Data Breach', 'Unauthorized Access', 'Retention Violation')")
    severity = dspy.OutputField(desc="Severity level (critical, high, medium, low, info)")
    violation_description = dspy.OutputField(desc="Detailed description of the potential violation")
    affected_requirements = dspy.OutputField(desc="Comma-separated affected regulatory requirements")
    potential_impact = dspy.OutputField(desc="Potential impact of the violation (fines, reputation, legal action, etc.)")
    remediation_steps = dspy.OutputField(desc="Comma-separated steps to remediate the violation")
    deadline = dspy.OutputField(desc="Deadline for remediation (YYYY-MM-DD format, if applicable)")
    escalation_needed = dspy.OutputField(desc="Whether escalation is needed (true/false)")


class ValidatePolicyCompliance(dspy.Signature):
    """
    Validate organizational policies against regulatory frameworks.
    
    Comprehensive analysis of policy documents to ensure they meet
    all requirements of specified compliance frameworks.
    """
    
    policy_document = dspy.InputField(desc="Full policy document text")
    framework = dspy.InputField(desc="Regulatory framework to validate against")
    
    overall_compliance_status = dspy.OutputField(desc="Overall compliance status (compliant, partial, non_compliant)")
    compliant_requirements = dspy.OutputField(desc="Comma-separated list of compliant requirements")
    non_compliant_requirements = dspy.OutputField(desc="Comma-separated list of non-compliant requirements")
    gaps_identified = dspy.OutputField(desc="Detailed description of gaps identified")
    priority_actions = dspy.OutputField(desc="Comma-separated priority actions to achieve compliance")
    compliance_score = dspy.OutputField(desc="Overall compliance score (0.0 to 1.0)")
    recommendations = dspy.OutputField(desc="Detailed recommendations for improving compliance")


class AssessPrivacyRisk(dspy.Signature):
    """
    Assess privacy risks for data processing activities.
    
    Conducts privacy impact assessment to identify and evaluate
    risks to data subjects.
    """
    
    processing_description = dspy.InputField(desc="Description of the data processing activity")
    data_types = dspy.InputField(desc="Types of data being processed")
    data_subjects = dspy.InputField(desc="Categories of data subjects affected")
    
    risk_level = dspy.OutputField(desc="Overall risk level (critical, high, medium, low)")
    identified_risks = dspy.OutputField(desc="Comma-separated identified privacy risks")
    likelihood_assessment = dspy.OutputField(desc="Likelihood of risks materializing")
    impact_assessment = dspy.OutputField(desc="Potential impact if risks materialize")
    mitigation_measures = dspy.OutputField(desc="Comma-separated recommended mitigation measures")
    residual_risk = dspy.OutputField(desc="Residual risk after mitigation")
    dpia_required = dspy.OutputField(desc="Whether a full Data Protection Impact Assessment is required (true/false)")

