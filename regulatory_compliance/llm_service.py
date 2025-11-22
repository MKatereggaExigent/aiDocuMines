"""
LLM Service Layer for Regulatory Compliance using DSPy.
Provides high-level services for compliance analysis, DSAR processing, and regulatory mapping.
"""

import dspy
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from .schemas import (
    RequirementMappingInput, RequirementMappingOutput,
    DSARProcessingInput, DSARProcessingOutput,
    DataInventoryInput, DataInventoryOutput,
    RedactionAnalysisInput, RedactionAnalysisOutput,
    ComplianceAlertInput, ComplianceAlertOutput,
    ComplianceFramework, ComplianceStatus, SeverityLevel, DSARRequestType, DataCategory
)
from .dspy_signatures import (
    MapRegulatoryRequirement, ProcessDSAR, AnalyzeDataInventory,
    AnalyzeRedaction, GenerateComplianceAlert, ValidatePolicyCompliance, AssessPrivacyRisk
)
from .models import RegulatoryRequirement, PolicyMapping, DSARRequest, DataInventory, RedactionTask, ComplianceAlert


class RequirementMapper:
    """
    Service for mapping organizational policies to regulatory requirements.
    Uses DSPy to analyze policies and identify compliance gaps.
    """
    
    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.mapper = dspy.ChainOfThought(MapRegulatoryRequirement)
    
    def map_requirement(self, input_data: RequirementMappingInput, compliance_run, user, client) -> RequirementMappingOutput:
        """
        Map policy to regulatory requirement and save to database.
        
        Args:
            input_data: Requirement mapping input
            compliance_run: ComplianceRun instance
            user: User performing the mapping
            client: Client organization
            
        Returns:
            RequirementMappingOutput with mapping results
        """
        # Run DSPy mapping
        result = self.mapper(
            policy_text=input_data.policy_text,
            framework=input_data.framework.value,
            requirement_id=input_data.requirement_id or ""
        )
        
        # Parse policy sections
        policy_sections = [s.strip() for s in result.policy_sections.split(',') if s.strip()]
        
        # Parse recommendations
        recommendations = [r.strip() for r in result.recommendations.split(',') if r.strip()]
        
        # Create output
        output = RequirementMappingOutput(
            requirement_id=result.requirement_id,
            requirement_text=result.requirement_text,
            requirement_category=result.requirement_category,
            compliance_status=ComplianceStatus(result.compliance_status),
            policy_sections=policy_sections,
            gap_analysis=result.gap_analysis,
            recommendations=recommendations,
            confidence=float(result.confidence)
        )
        
        # Save RegulatoryRequirement to database
        RegulatoryRequirement.objects.create(
            client=client,
            user=user,
            compliance_run=compliance_run,
            requirement_id=output.requirement_id,
            requirement_text=output.requirement_text,
            requirement_category=output.requirement_category,
            compliance_status=output.compliance_status.value,
            evidence=result.gap_analysis,
            gap_analysis=result.gap_analysis
        )
        
        # Save PolicyMapping to database
        PolicyMapping.objects.create(
            client=client,
            user=user,
            compliance_run=compliance_run,
            policy_name=f"Policy for {output.requirement_id}",
            policy_section=', '.join(policy_sections[:3]),  # First 3 sections
            requirement_id=output.requirement_id,
            mapping_confidence=output.confidence,
            gap_status='compliant' if output.compliance_status == ComplianceStatus.COMPLIANT else 'gap_identified',
            gap_description=result.gap_analysis if output.compliance_status != ComplianceStatus.COMPLIANT else None,
            recommendations=recommendations
        )
        
        return output


class DSARProcessor:
    """
    Service for processing Data Subject Access Requests.
    Uses DSPy to classify requests and recommend fulfillment actions.
    """
    
    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.processor = dspy.ChainOfThought(ProcessDSAR)
    
    def process_dsar(self, input_data: DSARProcessingInput, compliance_run, user, client) -> DSARProcessingOutput:
        """
        Process DSAR and save to database.
        
        Args:
            input_data: DSAR processing input
            compliance_run: ComplianceRun instance
            user: User processing the request
            client: Client organization
            
        Returns:
            DSARProcessingOutput with processing results
        """
        # Run DSPy processing
        result = self.processor(
            request_text=input_data.request_text,
            request_type=input_data.request_type.value,
            data_subject_info=json.dumps(input_data.data_subject_info)
        )
        
        # Parse data categories
        data_categories = [DataCategory(c.strip()) for c in result.data_categories_requested.split(',') if c.strip()]
        
        # Parse systems
        systems = [s.strip() for s in result.systems_to_search.split(',') if s.strip()]
        
        # Parse recommended actions
        actions = [a.strip() for a in result.recommended_actions.split(',') if a.strip()]
        
        # Parse deadline
        deadline = None
        if result.deadline:
            try:
                deadline = datetime.strptime(result.deadline, '%Y-%m-%d').date()
            except:
                pass
        
        # Create output
        output = DSARProcessingOutput(
            request_type=DSARRequestType(result.classified_request_type),
            data_categories_requested=data_categories,
            systems_to_search=systems,
            estimated_scope=result.estimated_scope,
            deadline=deadline,
            complexity_level=result.complexity_level,
            recommended_actions=actions,
            risk_assessment=result.risk_assessment
        )

        # Save to database
        DSARRequest.objects.create(
            client=client,
            user=user,
            compliance_run=compliance_run,
            request_type=output.request_type.value,
            data_subject_name=input_data.data_subject_info.get('name', 'Unknown'),
            data_subject_email=input_data.data_subject_info.get('email', ''),
            request_details=input_data.request_text,
            data_categories=[cat.value for cat in data_categories],
            systems_involved=systems,
            estimated_effort=result.estimated_scope,
            status='pending',
            deadline=deadline,
            fulfillment_notes=result.risk_assessment
        )

        return output


class DataInventoryAnalyzer:
    """
    Service for analyzing data processing activities.
    Uses DSPy to create comprehensive data inventory entries.
    """

    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.analyzer = dspy.ChainOfThought(AnalyzeDataInventory)

    def analyze(self, input_data: DataInventoryInput, compliance_run, user, client) -> DataInventoryOutput:
        """
        Analyze data processing activity and save to database.

        Args:
            input_data: Data inventory input
            compliance_run: ComplianceRun instance
            user: User performing the analysis
            client: Client organization

        Returns:
            DataInventoryOutput with analysis results
        """
        # Run DSPy analysis
        result = self.analyzer(
            system_description=input_data.system_description,
            data_flows=input_data.data_flows or "",
            purpose=input_data.purpose
        )

        # Parse data categories
        data_categories = [DataCategory(c.strip()) for c in result.data_categories.split(',') if c.strip()]

        # Parse processing purposes
        purposes = [p.strip() for p in result.processing_purposes.split(',') if p.strip()]

        # Parse data sources and recipients
        sources = [s.strip() for s in result.data_sources.split(',') if s.strip()]
        recipients = [r.strip() for r in result.data_recipients.split(',') if r.strip()]

        # Parse security measures
        security_measures = [m.strip() for m in result.security_measures.split(',') if m.strip()]

        # Parse cross-border transfers
        cross_border = result.cross_border_transfers.lower() == 'true'

        # Create output
        output = DataInventoryOutput(
            activity_name=result.activity_name,
            data_categories=data_categories,
            processing_purposes=purposes,
            legal_basis=result.legal_basis,
            data_sources=sources,
            data_recipients=recipients,
            retention_period=result.retention_period,
            security_measures=security_measures,
            cross_border_transfers=cross_border,
            risk_level=SeverityLevel(result.risk_level)
        )

        # Save to database
        DataInventory.objects.create(
            client=client,
            user=user,
            compliance_run=compliance_run,
            activity_name=output.activity_name,
            data_category=data_categories[0].value if data_categories else 'personal_identifiable',
            processing_purpose=purposes[0] if purposes else input_data.purpose,
            legal_basis=output.legal_basis,
            data_sources=sources,
            data_recipients=recipients,
            retention_period=output.retention_period,
            security_measures=security_measures,
            cross_border_transfer=cross_border,
            transfer_safeguards=', '.join(security_measures[:3]) if cross_border else None
        )

        return output


class ComplianceAlertGenerator:
    """
    Service for generating compliance alerts.
    Uses DSPy to identify violations and recommend remediation.
    """

    def __init__(self, lm: Optional[dspy.LM] = None):
        """Initialize with optional language model"""
        if lm:
            dspy.settings.configure(lm=lm)
        self.generator = dspy.ChainOfThought(GenerateComplianceAlert)

    def generate_alert(self, input_data: ComplianceAlertInput, compliance_run, user, client) -> ComplianceAlertOutput:
        """
        Generate compliance alert and save to database.

        Args:
            input_data: Compliance alert input
            compliance_run: ComplianceRun instance
            user: User generating the alert
            client: Client organization

        Returns:
            ComplianceAlertOutput with alert details
        """
        # Run DSPy generation
        result = self.generator(
            activity_description=input_data.activity_description,
            framework=input_data.framework.value,
            context=json.dumps(input_data.context) if input_data.context else ""
        )

        # Parse affected requirements
        requirements = [r.strip() for r in result.affected_requirements.split(',') if r.strip()]

        # Parse remediation steps
        remediation = [s.strip() for s in result.remediation_steps.split(',') if s.strip()]

        # Parse deadline
        deadline = None
        if result.deadline:
            try:
                deadline = datetime.strptime(result.deadline, '%Y-%m-%d').date()
            except:
                pass

        # Parse escalation
        escalation = result.escalation_needed.lower() == 'true'

        # Create output
        output = ComplianceAlertOutput(
            alert_type=result.alert_type,
            severity=SeverityLevel(result.severity),
            violation_description=result.violation_description,
            affected_requirements=requirements,
            potential_impact=result.potential_impact,
            remediation_steps=remediation,
            deadline=deadline,
            escalation_needed=escalation
        )

        # Save to database
        ComplianceAlert.objects.create(
            client=client,
            user=user,
            compliance_run=compliance_run,
            alert_type=output.alert_type,
            severity=output.severity.value,
            description=output.violation_description,
            affected_requirements=requirements,
            potential_impact=output.potential_impact,
            remediation_steps=remediation,
            status='open',
            deadline=deadline
        )

        return output

