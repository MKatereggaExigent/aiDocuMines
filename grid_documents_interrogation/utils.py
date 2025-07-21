import os
import json
import tiktoken  # for OpenAI token estimation
import pandas as pd
from urllib.parse import unquote
from langchain_ollama import ChatOllama
from openai import OpenAI

# Registry of model context limits (tokens)
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128000,
    "gpt-4": 128000,
    "gpt-3.5-turbo": 16000,
    "claude-2": 100000,
    "claude-3-opus": 200000,
    "llama2": 4096,
    "mistral": 8192,
    "minilm": 512,
    "default": 4096
}

def estimate_token_count(text, model="gpt-3.5-turbo"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def chunk_text_by_token_limit(text, model_name, max_reserved_tokens=1000):
    token_limit = MODEL_CONTEXT_WINDOWS.get(model_name, MODEL_CONTEXT_WINDOWS["default"])
    chunk_size = token_limit - max_reserved_tokens

    words = text.split()
    chunks, current_chunk, token_count = [], [], 0

    for word in words:
        token_count += 1
        current_chunk.append(word)
        if token_count >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk, token_count = [], 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def dispatch_to_llm(query_text, chunk, llm_config, previous_messages=None):
    provider = llm_config.get("provider", "openai")
    model = llm_config.get("model", "gpt-3.5-turbo")
    api_key = llm_config.get("api_key")
    endpoint = llm_config.get("endpoint")

    if provider == "openai":
        client = OpenAI(api_key=api_key) if api_key else OpenAI()

        # Construct message history
        messages = [
            {"role": "system", "content": "You are a data analysis assistant."}
        ]

        if previous_messages:

            # previous_messages = previous_messages[-10:]  # Keep last 10 turns

            for msg in previous_messages:
                role = msg.get("role")
                content = msg.get("content")

                # Fallback for legacy format with 'query'/'response'
                if not content:
                    if msg.get("query"):
                        role = "user"
                        content = msg.get("query")
                    elif msg.get("response"):
                        role = "assistant"
                        content = msg.get("response")

                if role and content and isinstance(content, str) and content.strip():
                    messages.append({"role": role, "content": content})
                else:
                    print(f"[⚠️ Skipping malformed message] {msg}")

        messages.append({"role": "user", "content": f"Document: {chunk}\n\nQuestion: {query_text}"})

        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=messages
        )
        return response.choices[0].message.content

    elif provider == "ollama":
        try:
            # Use service name as internal DNS hostname inside Docker
            chat = ChatOllama(model=model, base_url="http://ollama:11434")
            context = ""
            if previous_messages:
                for msg in previous_messages:
                    context += f"User: {msg.get('query')}\nAssistant: {msg.get('response')}\n"
            context += f"Document: {chunk}\n\nQuestion: {query_text}"
            return chat.invoke(context)
        except Exception as e:
            raise RuntimeError(f"Ollama invocation failed: {e}")

    elif provider == "langchain":
        raise NotImplementedError("LangChain support is not yet implemented.")

    elif provider == "mcp":
        raise NotImplementedError("MCP provider not yet integrated.")

    else:
        raise ValueError(f"Unsupported provider: {provider}")



'''
def dispatch_to_llm(query_text, chunk, llm_config, previous_messages=None):
    provider = llm_config.get("provider", "openai")
    model = llm_config.get("model", "gpt-3.5-turbo")
    api_key = llm_config.get("api_key")
    endpoint = llm_config.get("endpoint")

    if provider == "openai":
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": "You are a data analysis assistant."},
                {"role": "user", "content": f"Document: {chunk}\n\nQuestion: {query_text}"}
            ]
        )
        return response.choices[0].message.content

    elif provider == "ollama":
        chat = ChatOllama(model=model)
        return chat.invoke(f"Document: {chunk}\n\nQuestion: {query_text}")

    elif provider == "langchain":
        raise NotImplementedError("LangChain support is not yet implemented.")

    elif provider == "mcp":
        raise NotImplementedError("MCP provider not yet integrated.")

    else:
        raise ValueError(f"Unsupported provider: {provider}")
'''

def execute_file_query(query_text, file_path, llm_config, previous_messages=None):
    from .file_readers import read_file, convert_dataframe_to_text

    content, is_tabular = read_file(file_path)
    if content is None:
        raise ValueError("File content could not be read. Ensure the file format is supported.")
    if is_tabular:
        content = convert_dataframe_to_text(content)
    if not isinstance(content, str):
        content = str(content)
    if not content.strip():
        raise ValueError("The file appears empty or unreadable.")

    model_name = llm_config.get("model", "default")
    token_chunks = chunk_text_by_token_limit(content, model_name)

    answers = []
    for i, chunk in enumerate(token_chunks):
        try:
            print(f"[INFO] Sending chunk {i+1}/{len(token_chunks)} to LLM...")
            answer = dispatch_to_llm(query_text, chunk, llm_config, previous_messages=previous_messages)
            answers.append(answer)
        except Exception as e:
            print(f"[ERROR] Failed to process chunk {i+1}: {e}")
            answers.append(f"[Error processing chunk: {e}]")
    return "\n\n---\n\n".join(answers)


'''
def execute_file_query(query_text, file_path, llm_config):
    from .file_readers import read_file, convert_dataframe_to_text

    content, is_tabular = read_file(file_path)
    if content is None:
        raise ValueError("File content could not be read. Ensure the file format is supported.")
    if is_tabular:
        content = convert_dataframe_to_text(content)
    if not isinstance(content, str):
        content = str(content)
    if not content.strip():
        raise ValueError("The file appears empty or unreadable.")

    model_name = llm_config.get("model", "default")
    token_chunks = chunk_text_by_token_limit(content, model_name)

    answers = []
    for i, chunk in enumerate(token_chunks):
        try:
            print(f"[INFO] Sending chunk {i+1}/{len(token_chunks)} to LLM...")
            answer = dispatch_to_llm(query_text, chunk, llm_config)
            answers.append(answer)
        except Exception as e:
            print(f"[ERROR] Failed to process chunk {i+1}: {e}")
            answers.append(f"[Error processing chunk: {e}]")
    return "\n\n---\n\n".join(answers)
'''

def execute_db_query(query_text, connection_string, table_name, llm_config, stream=False, chunk_size=100, previous_messages=None):
    from .db_query_tools import fetch_column_names, generate_sql_query, execute_sql_query

    try:
        print(f"[DEBUG] Connecting to database using: {connection_string}")
        column_names = fetch_column_names(connection_string, table_name)
        print(f"[DEBUG] Retrieved columns: {column_names}")

        sql_query = generate_sql_query(table_name, query_text, column_names)
        if not sql_query:
            print(f"[INFO] SQL generation failed, using fallback: SELECT * FROM {table_name} LIMIT 100")
            sql_query = f"SELECT * FROM {table_name} LIMIT 100"

        print(f"[DEBUG] Final SQL Query: {sql_query}")
        result = execute_sql_query(connection_string, sql_query, stream=stream, chunk_size=chunk_size)

        # Normalize results to text for LLM
        text_data = ""
        if isinstance(result, pd.DataFrame):
            print(f"[DEBUG] Got DataFrame with shape: {result.shape}")
            text_data = result.to_csv(index=False)
        elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes, dict)):
            chunks = []
            for item in result:
                if isinstance(item, pd.DataFrame):
                    if not item.empty:
                        chunks.append(item.to_csv(index=False))
                else:
                    chunks.append(str(item))
            text_data = "\n\n".join(chunks)
        else:
            text_data = str(result)

        print(f"[DEBUG] Extracted text data length: {len(text_data)}")
        if not text_data.strip():
            print("[WARN] Query returned no usable data.")
            return "The table exists but contains no data rows to analyze."

        # Process with LLM
        model_name = llm_config.get("model", "default")
        token_chunks = chunk_text_by_token_limit(text_data, model_name)

        answers = []
        for i, chunk in enumerate(token_chunks):
            try:
                print(f"[INFO] Sending chunk {i+1}/{len(token_chunks)} to LLM...")
                answer = dispatch_to_llm(query_text, chunk, llm_config, previous_messages=previous_messages)
                answers.append(answer)
            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i+1}: {e}")
                answers.append(f"[Error processing chunk: {e}]")

        return "\n\n---\n\n".join(answers)

    except Exception as e:
        print(f"[FATAL] Unexpected error in DB query pipeline: {e}")
        return f"[ERROR] Database query failed: {str(e)}"


'''
def execute_db_query(query_text, connection_string, table_name, llm_config, stream=False, chunk_size=100):
    from .db_query_tools import fetch_column_names, generate_sql_query, execute_sql_query

    try:
        print(f"[DEBUG] Connecting to database using: {connection_string}")
        column_names = fetch_column_names(connection_string, table_name)
        print(f"[DEBUG] Retrieved columns: {column_names}")

        sql_query = generate_sql_query(table_name, query_text, column_names)
        if not sql_query:
            print(f"[INFO] SQL generation failed, using fallback: SELECT * FROM {table_name} LIMIT 100")
            sql_query = f"SELECT * FROM {table_name} LIMIT 100"

        print(f"[DEBUG] Final SQL Query: {sql_query}")
        result = execute_sql_query(connection_string, sql_query, stream=stream, chunk_size=chunk_size)

        # Normalize results to text for LLM
        text_data = ""
        if isinstance(result, pd.DataFrame):
            print(f"[DEBUG] Got DataFrame with shape: {result.shape}")
            text_data = result.to_csv(index=False)
        elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes, dict)):
            chunks = []
            for item in result:
                if isinstance(item, pd.DataFrame):
                    if not item.empty:
                        chunks.append(item.to_csv(index=False))
                else:
                    chunks.append(str(item))
            text_data = "\n\n".join(chunks)
        else:
            text_data = str(result)

        print(f"[DEBUG] Extracted text data length: {len(text_data)}")
        if not text_data.strip():
            print("[WARN] Query returned no usable data.")
            return "The table exists but contains no data rows to analyze."

        # Process with LLM
        model_name = llm_config.get("model", "default")
        token_chunks = chunk_text_by_token_limit(text_data, model_name)

        answers = []
        for i, chunk in enumerate(token_chunks):
            try:
                print(f"[INFO] Sending chunk {i+1}/{len(token_chunks)} to LLM...")
                answer = dispatch_to_llm(query_text, chunk, llm_config)
                answers.append(answer)
            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i+1}: {e}")
                answers.append(f"[Error processing chunk: {e}]")

        return "\n\n---\n\n".join(answers)

    except Exception as e:
        print(f"[FATAL] Unexpected error in DB query pipeline: {e}")
        return f"[ERROR] Database query failed: {str(e)}"
'''


def get_token_limit(model):
    return MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOWS["default"])

