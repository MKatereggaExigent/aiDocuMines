# Generated manually for multi-tenancy enforcement

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('custom_authentication', '0001_initial'),
        ('document_translation', '0002_alter_translationstorage_run'),
    ]

    operations = [
        migrations.AddField(
            model_name='translationrun',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='translation_runs', to='custom_authentication.client'),
        ),
    ]
