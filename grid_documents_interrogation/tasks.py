import gc
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .utils import execute_file_query, execute_db_query


@shared_task(soft_time_limit=300)
def process_file_query(query_text, file_path, llm_config: dict):
    """
    LLM config expected:
    {
        "provider": "openai" | "ollama" | "langchain" | "mcp",
        "model": "gpt-4o" | "llama2" | "mistral" | ...,
        "api_key": "...",     # Optional
        "endpoint": "...",    # Optional
        "other_config": {...} # Optional
    }
    """
    try:
        result = execute_file_query(query_text, file_path, llm_config)
        gc.collect()
        return result
    except SoftTimeLimitExceeded:
        return 'Task exceeded soft time limit'
    except Exception as e:
        return f'Error during file query: {str(e)}'


@shared_task(soft_time_limit=300)
def process_db_query(query_text, connection_string, table_name, llm_config: dict, stream=False):
    try:
        result = execute_db_query(query_text, connection_string, table_name, llm_config, stream=stream)
        gc.collect()
        if stream and hasattr(result, '__iter__'):
            return "\n\n".join([df.to_csv(index=False) for df in result])
        return result.to_csv(index=False) if hasattr(result, 'to_csv') else result
    except SoftTimeLimitExceeded:
        return 'Task exceeded soft time limit'
    except Exception as e:
        return f'Error during DB query: {str(e)}'

