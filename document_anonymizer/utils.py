import os
import json
import re
import logging
from django.conf import settings
from docx import Document
import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from unstructured.partition.pdf import partition_pdf
from document_anonymizer.models import Anonymize

logger = logging.getLogger(__name__)


class AnonymizationService:
    """
    Handles document extraction, full Presidio ➔ SpaCy anonymization pipeline, and de-anonymization.
    Now supports structured PDF extraction using unstructured.
    """

    def __init__(self):
        logger.info("📦 Initializing AnonymizationService with shared models...")
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.nlp = spacy.load("en_core_web_lg")  # Load once per task

    def extract_text_from_file(self, file_path):
        logger.info(f"🔄 Extracting text from: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None, [], []

        try:
            if file_path.lower().endswith(".pdf"):
                return self.extract_text_from_pdf(file_path)
            elif file_path.lower().endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read(), [], []
            elif file_path.lower().endswith(".docx"):
                return self.extract_text_from_docx(file_path), [], []
            else:
                logger.warning(f"⚠️ Unsupported file type: {file_path}")
                return None, [], []
        except Exception as e:
            logger.error(f"❌ Failed to extract text from {file_path}: {e}")
            return None, [], []

    def extract_structured_text(self, file_path):
        """
        Dynamically select the correct structured extraction function based on file type.
        """
        logger.info(f"📄 extract_structured_text() ➔ Processing {file_path}")
        try:
            if file_path.lower().endswith(".pdf"):
                from unstructured.partition.pdf import partition_pdf
                elements = partition_pdf(filename=file_path)
            elif file_path.lower().endswith(".docx"):
                from unstructured.partition.docx import partition_docx
                elements = partition_docx(filename=file_path)
            else:
                logger.warning(f"⚠️ Unsupported file type for structured extraction: {file_path}")
                return None, [], []

            structured_text = "\n\n".join(el.text.strip() for el in elements if el.text and el.text.strip())
            return structured_text, elements, [el.to_dict() for el in elements]
        except Exception as e:
            logger.error(f"❌ extract_structured_text() failed: {e}")
            return None, [], []


    def extract_text_from_pdf(self, file_path):
        try:
            logger.info(f"📄 Using unstructured to extract structured PDF text from: {file_path}")
            elements = partition_pdf(filename=file_path)
            structured_text = "\n\n".join(el.text.strip() for el in elements if el.text and el.text.strip())

            return structured_text, elements, [el.to_dict() for el in elements]
        except Exception as e:
            logger.error(f"❌ Structured PDF extraction failed via unstructured: {e}")
            return None, [], []

    def extract_text_from_docx(self, file_path):
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"❌ DOCX text extraction failed: {e}")
            return None
    
    def anonymize_text(self, text):
        """
        Anonymizes the input text using both Presidio and SpaCy engines.
        Reuses shared engine instances for performance and memory efficiency.
        """
        logger.info("🔄 Running Presidio anonymization...")
        presidio_results = self.analyzer.analyze(text=text, entities=[], language="en")
        presidio_map = {}
        presidio_counter = {}
        presidio_masked = text
    
        for result in presidio_results:
            entity_type = result.entity_type
            presidio_counter[entity_type] = presidio_counter.get(entity_type, 0) + 1
            mask = f"{entity_type}_MASKED_{presidio_counter[entity_type]}"
            value = text[result.start:result.end].strip()
            presidio_map[mask] = value
            presidio_masked = re.sub(r'\b' + re.escape(value) + r'\b', mask, presidio_masked, 1)
    
        logger.info("🔄 Running SpaCy anonymization...")
        spacy_map = {}
        spacy_counter = {}
        final_masked = presidio_masked
        doc = self.nlp(presidio_masked)
    
        for ent in doc.ents:
            entity_type = ent.label_
            spacy_counter[entity_type] = spacy_counter.get(entity_type, 0) + 1
            mask = f"{entity_type}_MASKED_{spacy_counter[entity_type]}"
            spacy_map[mask] = ent.text.strip()
            final_masked = re.sub(r'\b' + re.escape(ent.text.strip()) + r'\b', mask, final_masked, 1)
    
        combined_map = {**spacy_map, **presidio_map}
    
        logger.info(f"✅ Presidio map: {json.dumps(presidio_map, indent=2)}")
        logger.info(f"✅ SpaCy map: {json.dumps(spacy_map, indent=2)}")
    
        return final_masked, combined_map, presidio_map, spacy_map


    def deanonymize_pipeline(self, masked_text, spacy_mapping, presidio_mapping):
        partially_restored = self.reverse_masking(masked_text, spacy_mapping)
        fully_restored = self.reverse_masking(partially_restored, presidio_mapping)
        return fully_restored

    def reverse_masking(self, text, entity_mapping):
        for mask, original in sorted(entity_mapping.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = re.compile(r'\\b' + re.escape(mask) + r'\\b')
            text = pattern.sub(original, text)
        return text

    def get_file_path(self, original_file_path, folder="anonymized", extension="txt"):
        directory = os.path.join(os.path.dirname(original_file_path), folder)
        os.makedirs(directory, exist_ok=True)
        filename = os.path.basename(original_file_path).replace(".pdf", f".{extension}")
        return os.path.join(directory, filename)

    def update_block_text(self, structured_blocks, element_id, new_text):
        for block in structured_blocks:
            if block.get("element_id") == element_id:
                block["text"] = new_text
                return True
        return False

    def compute_risk_score(self, original_text, presidio_map, spacy_map):
        """
        Calculates the document risk score and entity breakdown based on Presidio + SpaCy results.
        """
        total_tokens = len(original_text.split())
        if total_tokens == 0:
            return {
                "risk_score": 0.0,
                "risk_level": "Low",
                "breakdown": {}
            }

        # Combine all entities
        all_entities = {**presidio_map, **spacy_map}
        total_sensitive_entities = len(all_entities)

        risk_score = round((total_sensitive_entities / total_tokens) * 100, 2)

        # Risk level thresholds
        if risk_score <= 10:
            risk_level = "Low"
        elif risk_score <= 30:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # Category breakdown
        entity_breakdown = {}
        for key in all_entities.keys():
            category = key.split("_MASKED_")[0]
            entity_breakdown[category] = entity_breakdown.get(category, 0) + 1

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "breakdown": entity_breakdown
        }



def generate_anonymized_html(masked_text, entity_mapping):
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Anonymized Document</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f7f9fc;
            color: #2e2e2e;
            line-height: 1.7;
        }
        h1, h2, h3 {
            color: #1a1a1a;
            margin-top: 2rem;
        }
        .masked {
            background-color: #fff3cd;
            color: #856404;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #ffeeba;
            cursor: help;
        }
        pre {
            background-color: #ffffff;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .container {
            max-width: 960px;
            margin: auto;
        }
        .toggle-map {
            margin-top: 10px;
            cursor: pointer;
            color: #007bff;
            text-decoration: underline;
        }
        #entity-map {
            display: none;
            margin-top: 10px;
        }
        footer {
            margin-top: 60px;
            font-size: 0.9rem;
            text-align: center;
            color: #888;
        }
    </style>
    <script>
        function toggleEntityMap() {
            var map = document.getElementById('entity-map');
            map.style.display = map.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>🛡️ Anonymized Document</h1>
        <pre>{text}</pre>
        <h3 class="toggle-map" onclick="toggleEntityMap()">📜 Show/Hide Entity Mapping</h3>
        <pre id="entity-map">{entity_map}</pre>
    </div>
    <footer>
        Generated by aiDocuMines &mdash; Preserving privacy, securely and beautifully.
    </footer>
</body>
</html>
"""
    highlighted_text = masked_text
    for mask, original in sorted(entity_mapping.items(), key=lambda x: len(x[0]), reverse=True):
        tooltip = f"title='Original: {original}'"
        highlighted_text = highlighted_text.replace(
            mask, f'<span class="masked" {tooltip}>{mask}</span>'
        )

    entity_map_json = json.dumps(entity_mapping, indent=4)
    return html_template.replace("{text}", highlighted_text).replace("{entity_map}", entity_map_json)

from docx import Document as DocxDocument

def summarize_blocks(blocks, element_ids, model="gpt-4"):
    """
    Dummy implementation for now. Replace with actual GPT-4 call.
    """
    results = []
    for block in blocks:
        if block.get("element_id") in element_ids:
            text = block.get("text", "")
            results.append({
                "element_id": block.get("element_id"),
                "summary": f"Summary of: {text[:60]}..."
            })
    return results


def update_structured_block(json_path, element_id, new_text):
    with open(json_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    updated = False
    for block in blocks:
        if block.get("element_id") == element_id:
            block["text"] = new_text
            updated = True
            break

    if updated:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(blocks, f, indent=2)

    return updated


def export_to_markdown(json_path, generate_preview=False):
    """
    Converts structured JSON blocks into a well-formatted Markdown document.
    - Adds a TOC (Table of Contents) based on Titles and Headers.
    - Formats tables and content semantically.
    - Optionally saves a plain-text preview for quick viewing.
    """
    import hashlib

    md_lines = []
    toc_lines = ["## 📚 Table of Contents\n"]

    with open(json_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    for i, block in enumerate(blocks):
        block_type = block.get("type", "Block")
        text = block.get("text", "").strip()

        # Generate an anchor-friendly heading ID
        hash_id = hashlib.md5(text.encode("utf-8")).hexdigest()[:6]

        if block_type.lower() in ["title", "header"]:
            toc_lines.append(f"- [{text}](#{hash_id})")
            md_lines.append(f"### <a name=\"{hash_id}\"></a>{text}\n")

        elif block_type.lower() in ["listitem", "unorderedlist", "orderedlist"]:
            items = text.split("\n")
            for item in items:
                md_lines.append(f"- {item.strip()}")
            md_lines.append("")  # Spacer

        elif block_type.lower() in ["table", "tabular"]:
            # Handle as Markdown table
            rows = [line for line in text.split("\n") if line.strip()]
            if len(rows) >= 2:
                header = rows[0].split()
                separator = ["---"] * len(header)
                md_lines.append("| " + " | ".join(header) + " |")
                md_lines.append("| " + " | ".join(separator) + " |")
                for row in rows[1:]:
                    cols = row.split()
                    md_lines.append("| " + " | ".join(cols) + " |")
            else:
                md_lines.append(f"```table\n{text}\n```")

        elif block_type.lower() == "narrativetext":
            md_lines.append(f"> {text}")

        else:
            md_lines.append(f"**{block_type}**\n\n{text}")

        md_lines.append("\n---\n")

    toc_text = "\n".join(toc_lines) + "\n---\n"
    full_md = toc_text + "\n".join(md_lines)

    md_path = json_path.replace(".json", ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    # Optional: Plain-text preview (no Markdown formatting)
    if generate_preview:
        preview_text = "\n".join([block.get("text", "").strip() for block in blocks])
        preview_path = json_path.replace(".json", "_preview.txt")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(preview_text)

    return md_path


def export_to_docx(json_path):
    doc = DocxDocument()
    with open(json_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    for block in blocks:
        doc.add_heading(block.get("type", "Block"), level=2)
        doc.add_paragraph(block.get("text", ""))

    out_path = json_path.replace(".json", ".docx")
    doc.save(out_path)
    return out_path


def compute_global_anonymization_stats(
    client_name=None,
    project_id=None,
    service_id=None,
    date_from=None,
    date_to=None
):
    """
    Computes anonymization stats, optionally filtered by client/project/service/date.
    """

    from django.db.models import Q

    filters = Q(is_active=True)

    if client_name:
        filters &= Q(run__client_name=client_name)
    if project_id:
        filters &= Q(run__project_id=project_id)
    if service_id:
        filters &= Q(run__service_id=service_id)
    if date_from:
        filters &= Q(updated_at__date__gte=date_from)
    if date_to:
        filters &= Q(updated_at__date__lte=date_to)

    queryset = Anonymize.objects.filter(filters)

    files_with_entities = 0
    files_without_entities = 0
    total_entities_anonymized = 0
    entity_type_breakdown = {}

    for record in queryset:
        combined_map = {}
        if record.presidio_masking_map:
            combined_map.update(record.presidio_masking_map)
        if record.spacy_masking_map:
            combined_map.update(record.spacy_masking_map)

        entity_counts = {}
        for mask, original in combined_map.items():
            entity_type = mask.split("_MASKED_")[0]
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        file_entity_total = sum(entity_counts.values())
        total_entities_anonymized += file_entity_total

        for entity_type, count in entity_counts.items():
            entity_type_breakdown[entity_type] = (
                entity_type_breakdown.get(entity_type, 0) + count
            )

        if file_entity_total > 0:
            files_with_entities += 1
        else:
            files_without_entities += 1

    result = {
        "files_with_entities": files_with_entities,
        "files_without_entities": files_without_entities,
        "total_entities_anonymized": total_entities_anonymized,
        "entity_type_breakdown": entity_type_breakdown,
    }

    return result

