# custom_authentication/middleware.py

from .models import UserAPICall

class APICallLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only log for authenticated users (you can modify this condition as needed)
        if request.user.is_authenticated:
            # Log the API call
            UserAPICall.objects.create(user=request.user, endpoint=request.path)
        
        # Call the next middleware or view
        response = self.get_response(request)
        return response
