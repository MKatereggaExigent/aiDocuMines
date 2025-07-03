# file_elasticsearch/utils.py

from elasticsearch_dsl import Search, Q
from core.elastic_indexes import FileIndex
from core.utils import extract_document_text


def delete_index():
    FileIndex._index.delete(ignore=404)

def create_index():
    FileIndex.init()

def index_file(file_instance):
    # 🔥 extract text from file path
    content_text = extract_document_text(file_instance.filepath)

    doc = FileIndex(
        meta={'id': str(file_instance.id)},
        id=str(file_instance.id),
        filename=file_instance.filename,
        filepath=file_instance.filepath,
        file_size=file_instance.file_size,
        status=file_instance.status,
        project_id=file_instance.project_id,
        service_id=file_instance.service_id,
        created_at=file_instance.created_at,
        updated_at=file_instance.updated_at,
        md5_hash=file_instance.md5_hash,
        user_id=file_instance.user.id if file_instance.user else None,
        content=content_text,   # ✅ save extracted text!
    )
    doc.save()

def force_reindex():
    from core.models import File
    delete_index()
    create_index()
    for f in File.objects.all():
        index_file(f)

def basic_search(query, scope="both"):
    s = Search(index='files')

    if not query:
        return []

    if scope == "filename":
        s = s.query(
            "multi_match",
            query=query,
            fields=["filename", "filepath"]
        )

    elif scope == "content":
        s = s.query(
            "match",
            content=query
        )

    elif scope == "both":
        s = s.query(
            "multi_match",
            query=query,
            fields=["filename", "filepath", "content"]
        )

    return s.execute()


def advanced_search(must=None, filter=None, search_in=None):
    must = must or []
    filter = filter or []
    search_in = search_in or ["filename", "content"]

    must_clauses = []
    for clause in must:
        field = clause["field"]
        value = clause["value"]

        if field == "content":
            must_clauses.append({
                "match": {
                    "content": value
                }
            })
        else:
            must_clauses.append({
                "wildcard": {
                    field: {
                        "value": value,
                        "case_insensitive": True
                    }
                }
            })

    filter_clauses = []
    for f in filter:
        field = f["field"]
        value = f["value"]
        filter_clauses.append({
            "term": {
                field: value
            }
        })

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        }
    }

    s = FileIndex.search().update_from_dict(body)
    results = s.execute()
    return results

