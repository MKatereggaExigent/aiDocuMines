from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from file_system.utils import get_user_file_tree
from file_system.tasks import generate_user_file_tree_task
from rest_framework import status
from celery.result import AsyncResult
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

class UserFileTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        run_async = request.query_params.get("async", "false").lower() == "true"

        if run_async:
            # Queue the task and return task_id
            task = generate_user_file_tree_task.delay(user_id)
            return Response({
                "message": "Task queued successfully",
                "task_id": task.id,
                "user_id": user_id
            }, status=status.HTTP_202_ACCEPTED)

        # Synchronous response
        file_tree = get_user_file_tree(user_id)
        return Response({
            "user_id": user_id,
            "structure": file_tree
        })


