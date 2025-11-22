"""
DSPy signatures for IP Litigation LLM processing.
Defines structured input/output interfaces for patent analysis tasks.
"""

import dspy


class ClassifyPatentDocument(dspy.Signature):
    """
    Classify a patent document and extract key metadata.
    
    Analyzes patent documents to determine type, extract bibliographic data,
    and identify technology areas and classifications.
    """
    
    document_text = dspy.InputField(desc="Full text of the patent document to classify")
    document_title = dspy.InputField(desc="Title of the document (if available)")
    
    document_type = dspy.OutputField(desc="Type of patent document (utility_patent, design_patent, etc.)")
    patent_number = dspy.OutputField(desc="Extracted patent number (e.g., US10123456B2)")
    application_number = dspy.OutputField(desc="Extracted application number")
    filing_date = dspy.OutputField(desc="Extracted filing date (YYYY-MM-DD format)")
    title = dspy.OutputField(desc="Patent title")
    abstract = dspy.OutputField(desc="Patent abstract summary")
    technology_area = dspy.OutputField(desc="Primary technology area (e.g., 'Software', 'Biotechnology', 'Mechanical Engineering')")
    ipc_classes = dspy.OutputField(desc="Comma-separated International Patent Classification codes")
    confidence = dspy.OutputField(desc="Classification confidence score (0.0 to 1.0)")


class ExtractPatentClaims(dspy.Signature):
    """
    Extract and analyze patent claims from a patent document.
    
    Identifies all claims, classifies them as independent or dependent,
    and extracts key claim limitations.
    """
    
    patent_text = dspy.InputField(desc="Full patent document text")
    patent_number = dspy.InputField(desc="Patent number for reference")
    
    claims_json = dspy.OutputField(desc="JSON array of claims with structure: [{claim_number, claim_type, claim_text, dependencies, key_limitations}]")
    total_claims = dspy.OutputField(desc="Total number of claims")
    independent_claims = dspy.OutputField(desc="Number of independent claims")
    dependent_claims = dspy.OutputField(desc="Number of dependent claims")


class AnalyzeInfringement(dspy.Signature):
    """
    Analyze potential patent infringement by comparing claims to an accused product.
    
    Performs element-by-element claim analysis and assesses infringement likelihood
    under literal infringement and doctrine of equivalents theories.
    """
    
    patent_claims = dspy.InputField(desc="Patent claims to analyze (one per line)")
    accused_product_description = dspy.InputField(desc="Detailed description of the accused product or process")
    patent_number = dspy.InputField(desc="Patent number being analyzed")
    
    infringement_likelihood = dspy.OutputField(desc="Overall infringement likelihood (very_low, low, medium, high, very_high)")
    infringement_types = dspy.OutputField(desc="Comma-separated potential infringement types (literal, doctrine_of_equivalents, indirect, etc.)")
    claim_by_claim_analysis = dspy.OutputField(desc="JSON object mapping claim numbers to analysis text")
    key_limitations_met = dspy.OutputField(desc="Comma-separated list of claim limitations met by accused product")
    key_limitations_not_met = dspy.OutputField(desc="Comma-separated list of claim limitations NOT met by accused product")
    equivalents_analysis = dspy.OutputField(desc="Analysis under doctrine of equivalents")
    recommendation = dspy.OutputField(desc="Overall recommendation (pursue litigation, monitor, no action, etc.)")
    confidence = dspy.OutputField(desc="Analysis confidence score (0.0 to 1.0)")


class AnalyzeValidity(dspy.Signature):
    """
    Analyze patent validity against prior art references.
    
    Evaluates validity challenges including anticipation, obviousness,
    and written description/enablement issues.
    """
    
    patent_claims = dspy.InputField(desc="Patent claims to analyze (one per line)")
    prior_art_references = dspy.InputField(desc="Prior art reference descriptions (one per line)")
    patent_number = dspy.InputField(desc="Patent number being analyzed")
    challenge_type = dspy.InputField(desc="Type of validity challenge (anticipation_102, obviousness_103, etc.)")
    
    success_likelihood = dspy.OutputField(desc="Likelihood of successful validity challenge (very_low, low, medium, high, very_high)")
    strongest_prior_art = dspy.OutputField(desc="Comma-separated list of strongest prior art references")
    claim_by_claim_analysis = dspy.OutputField(desc="JSON object mapping claim numbers to validity analysis")
    key_differences = dspy.OutputField(desc="Comma-separated key differences between claims and prior art")
    obviousness_rationale = dspy.OutputField(desc="Rationale for obviousness analysis (if applicable)")
    recommendation = dspy.OutputField(desc="Overall recommendation for validity challenge")
    confidence = dspy.OutputField(desc="Analysis confidence score (0.0 to 1.0)")


class GenerateClaimChart(dspy.Signature):
    """
    Generate a claim chart mapping patent claims to accused product features or prior art.
    
    Creates detailed element-by-element comparison for infringement or validity analysis.
    """
    
    patent_claims = dspy.InputField(desc="Patent claims to map (one per line)")
    comparison_subject = dspy.InputField(desc="Accused product description or prior art reference")
    chart_type = dspy.InputField(desc="Type of chart (infringement or invalidity)")
    patent_number = dspy.InputField(desc="Patent number")
    
    claim_chart_json = dspy.OutputField(desc="JSON array of claim chart entries: [{claim_element, accused_element, analysis, meets_limitation}]")
    overall_assessment = dspy.OutputField(desc="Overall assessment of infringement or invalidity")
    key_findings = dspy.OutputField(desc="Comma-separated key findings from the claim chart analysis")


class AnalyzePatentLandscape(dspy.Signature):
    """
    Analyze patent landscape for a technology area.
    
    Identifies key patents, trends, major players, and white space opportunities.
    """
    
    technology_area = dspy.InputField(desc="Technology area to analyze")
    patent_documents = dspy.InputField(desc="Patent documents in the landscape (titles and abstracts)")
    analysis_focus = dspy.InputField(desc="Focus of analysis (competitive intelligence, freedom to operate, etc.)")
    
    key_patents = dspy.OutputField(desc="Comma-separated list of key patent numbers and their significance")
    major_players = dspy.OutputField(desc="Comma-separated major patent holders in this space")
    technology_trends = dspy.OutputField(desc="Key technology trends identified")
    white_space_opportunities = dspy.OutputField(desc="Potential white space opportunities for innovation")
    risk_assessment = dspy.OutputField(desc="Overall patent risk assessment for this technology area")
    recommendations = dspy.OutputField(desc="Strategic recommendations based on landscape analysis")

