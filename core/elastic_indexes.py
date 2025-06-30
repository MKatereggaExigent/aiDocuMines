from elasticsearch_dsl import Document, Date, Keyword, Text, Integer
from elasticsearch_dsl.connections import connections


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
        name = 'runs'


class FileIndex(Document):
    id = Keyword()
    filename = Text()
    filepath = Text()
    file_size = Integer()
    status = Keyword()
    project_id = Keyword()
    service_id = Keyword()
    created_at = Date()
    updated_at = Date()
    md5_hash = Keyword()
    user_id = Integer()

    class Index:
        name = 'files'


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
        name = 'metadata'


class EndpointResponseTableIndex(Document):
    endpoint_name = Keyword()
    client = Keyword()
    status = Keyword()
    created_at = Date()
    updated_at = Date()

    class Index:
        name = 'endpoint_responses'


class WebhookIndex(Document):
    user = Keyword()
    webhook_url = Keyword()
    secret_key = Keyword()

    class Index:
        name = 'webhooks'

