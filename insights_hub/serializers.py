# insights_hub/serializers.py
from rest_framework import serializers

class MetricTotalsSerializer(serializers.Serializer):
    files = serializers.IntegerField(required=False, default=0)
    modified = serializers.IntegerField(required=False, default=0)
    atRisk = serializers.IntegerField(required=False, default=0)
    safe = serializers.IntegerField(required=False, default=0)
    pending = serializers.IntegerField(required=False, default=0)
    flagged = serializers.IntegerField(required=False, default=0)
    encrypted = serializers.IntegerField(required=False, default=0)
    anonymized = serializers.IntegerField(required=False, default=0)
    translated = serializers.IntegerField(required=False, default=0)
    insightsGenerated = serializers.IntegerField(required=False, default=0)
    complianceAlerts = serializers.IntegerField(required=False, default=0)

class TrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    value = serializers.IntegerField()

class DocTypeItemSerializer(serializers.Serializer):
    type = serializers.CharField()
    count = serializers.IntegerField()

class RecentFileSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    project = serializers.CharField(allow_null=True, required=False)
    size_bytes = serializers.IntegerField(allow_null=True, required=False)
    modified_at = serializers.DateTimeField(allow_null=True, required=False)
    status = serializers.CharField(allow_null=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)

class ComplianceAlertSerializer(serializers.Serializer):
    id = serializers.CharField()
    level = serializers.ChoiceField(choices=["info", "warning", "critical"])
    title = serializers.CharField()
    message = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField()
    project = serializers.CharField(allow_null=True, required=False)
    file_id = serializers.CharField(allow_null=True, required=False)
    rule = serializers.CharField(allow_null=True, required=False)

class StorageSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    files = serializers.IntegerField()
    encrypted = serializers.IntegerField()
    risk = serializers.IntegerField()

class HomeInsightsSerializer(serializers.Serializer):
    totals = MetricTotalsSerializer()
    volume_trend = TrendPointSerializer(many=True)
    doc_type_distribution = DocTypeItemSerializer(many=True)
    recent_files = RecentFileSerializer(many=True)
    alerts = ComplianceAlertSerializer(many=True)
    storages = StorageSummarySerializer(many=True)
    last_computed_at = serializers.DateTimeField()

