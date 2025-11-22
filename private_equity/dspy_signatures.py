"""
DSPy signatures for Private Equity LLM processing.
Defines structured LLM interactions for PE due diligence tasks.
"""
import dspy
from typing import List, Optional


# ============================================================================
# Document Classification Signature
# ============================================================================

class ClassifyPEDocument(dspy.Signature):
    """
    Classify a document in the context of Private Equity due diligence.
    Identify the document type, relevance, and priority for review.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the document to classify")
    deal_name = dspy.InputField(desc="Name of the M&A deal or transaction", default="")
    target_company = dspy.InputField(desc="Name of the target company", default="")
    
    # Outputs
    document_type = dspy.OutputField(desc="Type of document (e.g., 'nda', 'supplier_contract', 'financial_statement')")
    sub_type = dspy.OutputField(desc="More specific sub-type if applicable")
    confidence_score = dspy.OutputField(desc="Confidence score between 0.0 and 1.0")
    key_indicators = dspy.OutputField(desc="List of key phrases that led to this classification")
    relevance_to_dd = dspy.OutputField(desc="Relevance to due diligence (0.0 to 1.0)")
    priority = dspy.OutputField(desc="Review priority: critical, high, medium, or low")
    recommended_reviewers = dspy.OutputField(desc="List of recommended reviewer roles (e.g., 'legal', 'financial', 'technical')")
    reasoning = dspy.OutputField(desc="Explanation of the classification decision")


# ============================================================================
# Risk Clause Extraction Signature
# ============================================================================

class ExtractPERiskClauses(dspy.Signature):
    """
    Extract and analyze risky clauses from a document in PE due diligence context.
    Identify clauses that could impact the deal, their severity, and mitigation strategies.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the document to analyze")
    document_type = dspy.InputField(desc="Type of document being analyzed", default="")
    deal_type = dspy.InputField(desc="Type of deal: acquisition, merger, investment, or divestiture", default="acquisition")
    target_company = dspy.InputField(desc="Name of the target company", default="")
    focus_areas = dspy.InputField(desc="Specific risk areas to focus on (comma-separated)", default="")
    
    # Outputs
    risk_clauses_json = dspy.OutputField(desc="JSON array of risk clauses, each with: clause_text, risk_level, risk_category, impact_description, mitigation_suggestions, page_number, section")
    overall_risk_score = dspy.OutputField(desc="Overall risk score for the document (0.0 to 1.0)")
    summary = dspy.OutputField(desc="Executive summary of the risks found")
    deal_impact = dspy.OutputField(desc="Overall impact on the deal")
    recommendations = dspy.OutputField(desc="High-level recommendations for addressing the risks")


# ============================================================================
# Due Diligence Findings Generation Signature
# ============================================================================

class GenerateDDFindings(dspy.Signature):
    """
    Generate comprehensive due diligence findings report from analyzed documents.
    Synthesize document classifications and risk analyses into actionable insights.
    """
    # Inputs
    deal_name = dspy.InputField(desc="Name of the M&A deal or transaction")
    target_company = dspy.InputField(desc="Name of the target company")
    deal_type = dspy.InputField(desc="Type of deal: acquisition, merger, investment, or divestiture")
    document_summary = dspy.InputField(desc="JSON summary of classified documents with counts by type")
    risk_summary = dspy.InputField(desc="JSON summary of risk clauses by category and severity")
    key_documents = dspy.InputField(desc="List of key documents reviewed (comma-separated)")
    focus_areas = dspy.InputField(desc="Specific areas to focus on in the report", default="")
    
    # Outputs
    executive_summary = dspy.OutputField(desc="Executive summary of the due diligence findings (2-3 paragraphs)")
    key_findings_json = dspy.OutputField(desc="JSON array of key findings, each with: title, description, severity, category, supporting_documents, recommendations")
    recommendations_json = dspy.OutputField(desc="JSON array of recommendations, each with: title, description, priority, action_items, responsible_party")
    overall_risk_assessment = dspy.OutputField(desc="Overall risk assessment (low, medium, high, critical)")
    deal_recommendation = dspy.OutputField(desc="Recommendation on whether to proceed with the deal, with detailed reasoning")
    confidence_score = dspy.OutputField(desc="Confidence in the analysis (0.0 to 1.0)")
    reasoning = dspy.OutputField(desc="Explanation of how the findings were derived")


# ============================================================================
# Document Q&A Signature
# ============================================================================

class AnswerPEQuestion(dspy.Signature):
    """
    Answer questions about documents in the context of PE due diligence.
    Provide accurate, sourced answers with references to specific documents.
    """
    # Inputs
    question = dspy.InputField(desc="The question to answer")
    document_context = dspy.InputField(desc="Relevant document excerpts and metadata")
    deal_name = dspy.InputField(desc="Name of the M&A deal", default="")
    target_company = dspy.InputField(desc="Name of the target company", default="")
    
    # Outputs
    answer = dspy.OutputField(desc="Detailed answer to the question")
    confidence_score = dspy.OutputField(desc="Confidence in the answer (0.0 to 1.0)")
    source_documents = dspy.OutputField(desc="List of source documents used to answer the question")
    relevant_excerpts = dspy.OutputField(desc="Relevant excerpts from the documents that support the answer")
    follow_up_questions = dspy.OutputField(desc="Suggested follow-up questions")


# ============================================================================
# Key Information Extraction Signature
# ============================================================================

class ExtractPEKeyInfo(dspy.Signature):
    """
    Extract key information from PE documents (e.g., parties, dates, amounts, terms).
    Structure the information as key-value pairs with confidence scores.
    """
    # Inputs
    document_text = dspy.InputField(desc="The full text of the document")
    document_type = dspy.InputField(desc="Type of document", default="")
    extraction_fields = dspy.InputField(desc="Specific fields to extract (comma-separated)", default="parties,effective_date,termination_date,contract_value,key_terms")
    
    # Outputs
    key_values_json = dspy.OutputField(desc="JSON array of extracted key-value pairs, each with: key, value, confidence, source_text")
    summary = dspy.OutputField(desc="Summary of the key information extracted")
    completeness_score = dspy.OutputField(desc="How complete the extraction is (0.0 to 1.0)")

