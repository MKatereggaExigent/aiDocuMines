# document_structures/models.py

from django.db import models
from core.models import File, Run, User
import uuid


class DocumentStructureRun(models.Model):
    """
    Tracks a single document partitioning/extraction run via unstructured.
    One run may produce many DocumentElement rows for the same file.
    """
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    PARTITION_STRATEGY_CHOICES = [
        ("partition_pdf", "partition_pdf"),
        ("partition_text", "partition_text"),
        ("partition_auto", "partition_auto"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="structure_runs")
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="structure_runs")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="structure_runs")

    partition_strategy = models.CharField(
        max_length=50,
        choices=PARTITION_STRATEGY_CHOICES,
        default="partition_auto"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DocStructRun {self.id} - {self.partition_strategy} - {self.status}"


class DocumentElement(models.Model):
    """
    Stores each element extracted from the document by unstructured.
    E.g. Title, Text, NarrativeText, Address, ListItem, Footer, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(DocumentStructureRun, on_delete=models.CASCADE, related_name="elements")

    # Core element properties
    element_type = models.CharField(max_length=100, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    # Hierarchical relationship (e.g. list structure, nested sections)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children"
    )

    # Layout details
    page_number = models.IntegerField(blank=True, null=True)
    coordinates = models.JSONField(blank=True, null=True, help_text="Bounding boxes, polygons, etc.")
    order = models.PositiveIntegerField(default=0, db_index=True)

    # New fields supporting advanced unstructured features
    embedding = models.JSONField(blank=True, null=True, help_text="Optional vector embedding of the element text.")
    languages = models.JSONField(blank=True, null=True, help_text="List of language codes detected in this element.")
    list_level = models.IntegerField(blank=True, null=True, help_text="Nesting level if this is a list item.")
    list_item = models.CharField(max_length=255, blank=True, null=True, help_text="Bullet or number string of a list item.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["run", "order"]),
        ]

    def __str__(self):
        snippet = (self.text or "")[:50].replace("\n", " ")
        return f"[{self.element_type}] {snippet}"


class DocumentTable(models.Model):
    """
    Stores full tables extracted from the document by unstructured.
    Useful for downstream analytics, compliance, and data mining.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(DocumentStructureRun, on_delete=models.CASCADE, related_name="tables")

    page_number = models.IntegerField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    # Storing tables in multiple formats for flexibility
    html = models.TextField(blank=True, null=True, help_text="HTML table representation.")
    csv = models.TextField(blank=True, null=True, help_text="CSV table representation.")
    json = models.JSONField(blank=True, null=True, help_text="JSON representation (e.g. rows/columns).")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Table {self.id}"


class DocumentTableCell(models.Model):
    """
    Optional cell-level granularity for precise table analysis.
    E.g. extracting financial figures, cross-document cell comparisons.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(DocumentTable, on_delete=models.CASCADE, related_name="cells")

    row_idx = models.IntegerField()
    col_idx = models.IntegerField()
    text = models.TextField(blank=True, null=True)

    rowspan = models.IntegerField(default=1)
    colspan = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["table", "row_idx", "col_idx"]),
        ]

    def __str__(self):
        snippet = (self.text or "")[:30].replace("\n", " ")
        return f"Cell R{self.row_idx} C{self.col_idx}: {snippet}"


class DocumentComparison(models.Model):
    """
    Stores a comparison between two document structure runs.
    Tracks similarity scores and structural differences.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    run_1 = models.ForeignKey(DocumentStructureRun, on_delete=models.CASCADE, related_name="comparisons_as_first")
    run_2 = models.ForeignKey(DocumentStructureRun, on_delete=models.CASCADE, related_name="comparisons_as_second")

    lexical_similarity = models.FloatField(blank=True, null=True)
    semantic_similarity = models.FloatField(blank=True, null=True)
    deviation_report = models.JSONField(blank=True, null=True, help_text="Detailed differences between sections, if computed.")

    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Processing', 'Processing'),
            ('Completed', 'Completed'),
            ('Failed', 'Failed'),
        ],
        default='Pending',
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comparison {self.id}"


class SectionEdit(models.Model):
    """
    Tracks user edits to document sections for auditing and traceability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    element = models.ForeignKey(DocumentElement, on_delete=models.CASCADE, related_name="edits")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="document_section_edits")
    original_text = models.TextField(blank=True, null=True)
    edited_text = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Edit for Element {self.element_id}"


class DocumentElementPairComparison(models.Model):
    """
    Stores the similarity score between two specific document elements
    during a document comparison run.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    comparison = models.ForeignKey(
        DocumentComparison,
        on_delete=models.CASCADE,
        related_name="element_pairs",
    )

    element_type = models.CharField(max_length=100, blank=True, null=True)

    element_1 = models.ForeignKey(
        DocumentElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="as_element_1_in_comparisons"
    )
    element_2 = models.ForeignKey(
        DocumentElement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="as_element_2_in_comparisons"
    )

    text1 = models.TextField(blank=True, null=True)
    text2 = models.TextField(blank=True, null=True)

    lexical_similarity = models.FloatField(blank=True, null=True)
    semantic_similarity = models.FloatField(blank=True, null=True)

    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["comparison", "element_type"]),
        ]

    def __str__(self):
        return f"PairComparison {self.id} ({self.element_type})"

