from elasticsearch_dsl import Document, Date, Keyword, Text, Integer, Long
from elasticsearch_dsl.connections import connections

try:
    from document_search import config
    ES_SHARDS = getattr(config, "ES_SHARDS", 3)
    ES_REPLICAS = getattr(config, "ES_REPLICAS", 1)
except ImportError:
    ES_SHARDS = 3
    ES_REPLICAS = 1


class RunIndex(Document):
    run_id = Keyword()
    user = Keyword()
    status = Keyword()
    unique_code = Keyword()
    characters = Integer()
    cost = Integer()
    created_at = Date()
    updated_at = Date()

    class Index:
        name = "runs"


class FileIndex(Document):
    id = Keyword()
    filename = Text(
        analyzer="standard",
        fields={"raw": Keyword(), "trigram": Text(analyzer="trigram")},
    )
    filepath = Text(
        analyzer="standard",
        fields={"raw": Keyword(), "trigram": Text(analyzer="trigram")},
    )
    file_size = Integer()
    status = Keyword()
    project_id = Keyword()
    service_id = Keyword()
    created_at = Date()
    updated_at = Date()
    md5_hash = Keyword()
    user_id = Long()
    client_id = Keyword()
    content = Text(analyzer="english")

    class Index:
        name = "files"
        settings = {
            "number_of_shards": ES_SHARDS,
            "number_of_replicas": ES_REPLICAS,
            "analysis": {
                "analyzer": {
                    "trigram": {
                        "type": "custom",
                        "tokenizer": "trigram",
                    }
                },
                "tokenizer": {
                    "trigram": {
                        "type": "ngram",
                        "min_gram": 3,
                        "max_gram": 4,
                    }
                },
            },
        }


class MetadataIndex(Document):
    file = Keyword()
    title = Text()
    keywords = Text()
    author = Text()
    subject = Text()
    creator = Text()
    producer = Text()
    creationdate = Date()
    moddate = Date()
    page_count = Integer()
    pdf_version = Keyword()

    class Index:
        name = "metadata"


class EndpointResponseTableIndex(Document):
    endpoint_name = Keyword()
    client = Keyword()
    status = Keyword()
    created_at = Date()
    updated_at = Date()

    class Index:
        name = "endpoint_responses"


class WebhookIndex(Document):
    user = Keyword()
    webhook_url = Keyword()
    secret_key = Keyword()

    class Index:
        name = "webhooks"
