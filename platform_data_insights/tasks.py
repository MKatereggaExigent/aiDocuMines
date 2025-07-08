# platform_data_insights/tasks.py

from celery import shared_task
from django.utils import timezone
from .models import UserInsights
from .utils import calculate_user_insights
from django.core.serializers.json import DjangoJSONEncoder
import json


@shared_task
def generate_insights_for_user(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {"error": f"User {user_id} not found"}

    # Compute insights
    insights_data = calculate_user_insights(user)

    # Convert to JSON string, then back to dict
    safe_insights_json = json.dumps(insights_data, cls=DjangoJSONEncoder)
    insights_data = json.loads(safe_insights_json)

    # Save to DB
    UserInsights.objects.create(
        user=user,
        insights_data=insights_data,
        generated_at=timezone.now(),
        generated_async=True,
    )

    return insights_data

