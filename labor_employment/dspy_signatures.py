"""
DSPy Signatures for Labor & Employment LLM processing.
"""
import dspy


class AnalyzeCommunication(dspy.Signature):
    """Analyze workplace communication for sentiment, toxicity, and compliance issues"""
    
    # Inputs
    message_content: str = dspy.InputField(desc="The communication message content")
    message_type: str = dspy.InputField(desc="Type of message (email, slack, teams, etc.)")
    sender: str = dspy.InputField(desc="Message sender")
    recipients: str = dspy.InputField(desc="Comma-separated list of recipients")
    case_type: str = dspy.InputField(desc="Type of employment case (discrimination, harassment, etc.)")
    
    # Outputs
    sentiment_level: str = dspy.OutputField(desc="Sentiment level: very_positive, positive, neutral, negative, very_negative")
    sentiment_score: str = dspy.OutputField(desc="Sentiment score from -1.0 to 1.0")
    toxicity_level: str = dspy.OutputField(desc="Toxicity level: none, low, medium, high, severe")
    toxicity_score: str = dspy.OutputField(desc="Toxicity score from 0.0 to 1.0")
    relevance_score: str = dspy.OutputField(desc="Relevance to case from 0.0 to 1.0")
    is_privileged: str = dspy.OutputField(desc="true if attorney-client privileged, false otherwise")
    contains_pii: str = dspy.OutputField(desc="true if contains PII, false otherwise")
    is_flagged: str = dspy.OutputField(desc="true if should be flagged for review, false otherwise")
    flag_reason: str = dspy.OutputField(desc="Reason for flagging (empty if not flagged)")
    key_topics: str = dspy.OutputField(desc="Comma-separated list of key topics discussed")
    confidence_score: str = dspy.OutputField(desc="Confidence in analysis from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the analysis")


class AnalyzePolicyCompliance(dspy.Signature):
    """Analyze company policy compliance based on workplace communications"""
    
    # Inputs
    policy_text: str = dspy.InputField(desc="The company policy text")
    policy_type: str = dspy.InputField(desc="Type of policy (harassment, discrimination, etc.)")
    communications_sample: str = dspy.InputField(desc="Sample of workplace communications to analyze")
    company_name: str = dspy.InputField(desc="Name of the company")
    
    # Outputs
    compliance_score: str = dspy.OutputField(desc="Overall compliance score from 0.0 to 1.0")
    violations_json: str = dspy.OutputField(desc="JSON array of policy violations with type, severity, description, evidence, recommendation")
    gaps_json: str = dspy.OutputField(desc="JSON array of policy gaps identified")
    recommendations_json: str = dspy.OutputField(desc="JSON array of recommendations for improvement")
    confidence_score: str = dspy.OutputField(desc="Confidence in analysis from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the compliance analysis")


class AnalyzeWageHour(dspy.Signature):
    """Analyze potential wage and hour violations based on communication patterns"""
    
    # Inputs
    employee_name: str = dspy.InputField(desc="Employee name")
    job_title: str = dspy.InputField(desc="Employee job title")
    hourly_rate: str = dspy.InputField(desc="Hourly rate (if known)")
    analysis_period_days: str = dspy.InputField(desc="Number of days in analysis period")
    early_morning_messages: str = dspy.InputField(desc="Number of messages sent before 7 AM")
    late_evening_messages: str = dspy.InputField(desc="Number of messages sent after 7 PM")
    weekend_messages: str = dspy.InputField(desc="Number of messages sent on weekends")
    total_hours_worked: str = dspy.InputField(desc="Total hours worked in period")
    
    # Outputs
    potential_overtime_violations: str = dspy.OutputField(desc="true if potential overtime violations detected, false otherwise")
    potential_break_violations: str = dspy.OutputField(desc="true if potential break violations detected, false otherwise")
    potential_meal_violations: str = dspy.OutputField(desc="true if potential meal break violations detected, false otherwise")
    estimated_unpaid_hours: str = dspy.OutputField(desc="Estimated unpaid hours")
    estimated_unpaid_amount: str = dspy.OutputField(desc="Estimated unpaid amount in dollars (if hourly rate known)")
    violation_details_json: str = dspy.OutputField(desc="JSON array of violation details")
    recommendations_json: str = dspy.OutputField(desc="JSON array of recommendations")
    confidence_score: str = dspy.OutputField(desc="Confidence in analysis from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the wage & hour analysis")


class DetectCommunicationPatterns(dspy.Signature):
    """Detect patterns in workplace communications that may indicate employment issues"""
    
    # Inputs
    communications_json: str = dspy.InputField(desc="JSON array of communications with sender, recipients, content, timestamp")
    key_personnel: str = dspy.InputField(desc="Comma-separated list of key personnel to focus on")
    case_type: str = dspy.InputField(desc="Type of employment case")
    analysis_period: str = dspy.InputField(desc="Time period being analyzed")
    
    # Outputs
    patterns_json: str = dspy.OutputField(desc="JSON array of detected patterns with type, description, severity_score, participants, frequency, evidence_messages")
    risk_assessment: str = dspy.OutputField(desc="Overall risk assessment based on patterns")
    recommendations_json: str = dspy.OutputField(desc="JSON array of recommendations based on patterns")
    confidence_score: str = dspy.OutputField(desc="Confidence in pattern detection from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the pattern analysis")


class GenerateEEOCAnalysis(dspy.Signature):
    """Generate EEOC complaint analysis based on communications and evidence"""
    
    # Inputs
    complaint_type: str = dspy.InputField(desc="Type of EEOC complaint")
    complainant_name: str = dspy.InputField(desc="Name of complainant")
    company_name: str = dspy.InputField(desc="Name of company")
    relevant_communications: str = dspy.InputField(desc="Summary of relevant communications")
    timeline: str = dspy.InputField(desc="Timeline of events")
    
    # Outputs
    evidence_strength_score: str = dspy.OutputField(desc="Strength of evidence from 0.0 to 1.0")
    key_evidence_points_json: str = dspy.OutputField(desc="JSON array of key evidence points")
    legal_theories_json: str = dspy.OutputField(desc="JSON array of applicable legal theories")
    recommendations_json: str = dspy.OutputField(desc="JSON array of recommendations for the case")
    settlement_likelihood: str = dspy.OutputField(desc="Likelihood of settlement: low, medium, high")
    confidence_score: str = dspy.OutputField(desc="Confidence in analysis from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the EEOC analysis")


class ValidateComplianceAlert(dspy.Signature):
    """Validate and prioritize compliance alerts"""
    
    # Inputs
    alert_type: str = dspy.InputField(desc="Type of compliance alert")
    alert_description: str = dspy.InputField(desc="Description of the alert")
    related_messages: str = dspy.InputField(desc="Related communication messages")
    company_policies: str = dspy.InputField(desc="Relevant company policies")
    
    # Outputs
    is_valid_alert: str = dspy.OutputField(desc="true if valid alert, false if false positive")
    severity: str = dspy.OutputField(desc="Severity: low, medium, high, critical")
    priority: str = dspy.OutputField(desc="Priority: low, medium, high, urgent")
    recommended_action: str = dspy.OutputField(desc="Recommended action to take")
    escalation_needed: str = dspy.OutputField(desc="true if escalation needed, false otherwise")
    confidence_score: str = dspy.OutputField(desc="Confidence in validation from 0.0 to 1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of the validation")

