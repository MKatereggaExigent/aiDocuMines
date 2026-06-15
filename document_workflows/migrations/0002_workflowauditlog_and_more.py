import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document_workflows', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowstep',
            name='sla_hours',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workflowstep',
            name='escalation_user',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='workflowstep',
            name='approval_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflowstep',
            name='notify_on_completion',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflowassignment',
            name='sla_deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workflowassignment',
            name='escalated',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflowassignment',
            name='escalated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workflowassignment',
            name='escalated_to',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='workflowassignment',
            name='escalation_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workflowrun',
            name='sla_deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='WorkflowAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=50)),
                ('actor', models.CharField(max_length=255)),
                ('details', models.JSONField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='document_workflows.workflowrun')),
                ('step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='document_workflows.workflowstep')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
