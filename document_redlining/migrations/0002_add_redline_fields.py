from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('document_redlining', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='redliningresult',
            name='author',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='redliningresult',
            name='comparison_date',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name='redliningresult',
            name='comparison_stats',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='redliningresult',
            name='redline_docx_path',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
        migrations.AddField(
            model_name='redliningresult',
            name='redline_pdf_path',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
