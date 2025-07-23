from celery import shared_task
from file_system.utils import get_user_file_tree

@shared_task
def generate_user_file_tree_task(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.get(id=user_id)
    return {"user_id": user.id, "structure": get_user_file_tree(user)}


'''
@shared_task
def generate_user_file_tree_task(user_id):
    """
    Celery task to generate the file tree structure for a given user.
    """
    return {
        "user_id": user_id,
        "structure": get_user_file_tree(user_id)
    }
'''
