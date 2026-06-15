# Generated manually for multi-tenancy enforcement

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('custom_authentication', '0001_initial'),
        ('document_anonymizer', '0002_anonymizationstats'),
    ]

    operations = [
        migrations.AddField(
            model_name='anonymizationrun',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='anonymization_runs', to='custom_authentication.client'),
        ),
    ]
