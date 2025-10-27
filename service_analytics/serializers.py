from rest_framework import serializers


class ServiceExecutionSerializer(serializers.Serializer):
    """Serializer for individual service execution records"""
    id = serializers.UUIDField()
    vertical = serializers.CharField()
    service_type = serializers.CharField()
    service_name = serializers.CharField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    execution_time_seconds = serializers.IntegerField(allow_null=True)
    output_count = serializers.IntegerField()
    output_type = serializers.CharField()
    error_message = serializers.CharField(allow_blank=True)


class VerticalBreakdownSerializer(serializers.Serializer):
    """Serializer for vertical-level statistics"""
    vertical = serializers.CharField()
    total_executions = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    running = serializers.IntegerField()
    pending = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_execution_time = serializers.FloatField(allow_null=True)


class ServiceBreakdownSerializer(serializers.Serializer):
    """Serializer for service-level statistics"""
    service_type = serializers.CharField()
    service_name = serializers.CharField()
    vertical = serializers.CharField()
    count = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_execution_time = serializers.FloatField(allow_null=True)


class OverviewSerializer(serializers.Serializer):
    """Serializer for overall analytics overview"""
    total_executions = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    running = serializers.IntegerField()
    pending = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_output_files = serializers.IntegerField()
    avg_execution_time = serializers.FloatField(allow_null=True)
    verticals_breakdown = VerticalBreakdownSerializer(many=True)
    most_used_services = ServiceBreakdownSerializer(many=True)


class TrendDataPointSerializer(serializers.Serializer):
    """Serializer for time-series data points"""
    date = serializers.DateField()
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()


class TrendsSerializer(serializers.Serializer):
    """Serializer for trends data"""
    period = serializers.CharField()
    data_points = TrendDataPointSerializer(many=True)

