# db_query_tools.py

import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, inspect
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from urllib.parse import unquote
from sqlalchemy.engine.url import make_url


# Initialize LLaMA model from Ollama
llama = ChatOllama(model="llama3.1:latest", temperature=0.5)


def safe_create_engine(connection_string):
    try:
        # Unquote password and parse properly
        parsed_url = make_url(unquote(connection_string))
        return create_engine(parsed_url)
    except Exception as e:
        print(f"[❌ ERROR in safe_create_engine]: {e}")
        raise

def fetch_tables(connection_string):
    """List all available tables in the database."""
    try:
        engine = safe_create_engine(connection_string)  # create_engine(connection_string)
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        print(f"[Error] Failed to fetch tables: {e}")
        return []


def fetch_column_names(connection_string, table):
    """Fetch all column names from a given table."""
    try:
        engine = safe_create_engine(connection_string) # create_engine(connection_string)
        inspector = inspect(engine)
        columns = inspector.get_columns(table)
        return [col['name'] for col in columns]
    except Exception as e:
        print(f"[Error] Failed to fetch columns: {e}")
        return []


def generate_sql_query(table, user_query, column_names):
    columns_str = ", ".join(column_names)
    prompt = f"""
    Convert the following natural language request into a SQL query for the table `{table}`.
    Available columns: {columns_str}

    Request: {user_query}
    Only return the SQL query.
    """
    try:
        template = ChatPromptTemplate.from_template(prompt)
        parser = StrOutputParser()
        chain = template | llama | parser
        sql_query = chain.invoke({"question": user_query})

        print(f"[🧠 SQL GENERATED]: {sql_query.strip()}")
        return sql_query.strip().rstrip(";")
    except Exception as e:
        print(f"[❌ SQL GENERATION FAILED]: {e}")
        return f"SELECT * FROM {table} LIMIT 100"


def execute_sql_query(connection_string, sql_query, stream=False, chunk_size=100):
    """Run the SQL query and return results either all-at-once or in chunks."""
    try:
        engine = safe_create_engine(connection_string) # create_engine(connection_string)
        with engine.connect() as connection:
            if stream:
                result = connection.execution_options(stream_results=True).execute(sqlalchemy.text(sql_query))
                while True:
                    rows = result.fetchmany(chunk_size)
                    if not rows:
                        break
                    yield pd.DataFrame(rows, columns=result.keys())
            else:
                return pd.read_sql_query(sql_query, con=connection)
    except Exception as e:
        print(f"[Error] SQL execution failed: {e}")
        return pd.DataFrame([{"error": str(e)}])

