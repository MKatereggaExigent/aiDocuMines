# document_search/milvus_client.py
from pymilvus import connections
from .config import MILVUS_HOST, MILVUS_PORT

def get_milvus_connection():
    return connections.connect(
        alias="default", host=MILVUS_HOST, port=MILVUS_PORT
    )

