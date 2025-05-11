# db_meta_views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from .db_query_tools import fetch_tables, fetch_column_names


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_db_connection(request):
    connection_string = request.data.get("connection_string")

    if not connection_string:
        return Response({"error": "Missing connection_string"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            # conn.execute("SELECT 1")
            conn.execute(text("SELECT 1"))
        return Response({"success": True, "message": "Connection successful"})
    except SQLAlchemyError as e:
        return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def list_tables(request):
    connection_string = request.data.get("connection_string")

    if not connection_string:
        return Response({"error": "Missing connection_string"}, status=status.HTTP_400_BAD_REQUEST)

    tables = fetch_tables(connection_string)
    return Response({"tables": tables})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def list_columns(request):
    connection_string = request.data.get("connection_string")
    table = request.data.get("table")

    if not connection_string or not table:
        return Response({"error": "connection_string and table are required"}, status=status.HTTP_400_BAD_REQUEST)

    columns = fetch_column_names(connection_string, table)
    return Response({"columns": columns})

