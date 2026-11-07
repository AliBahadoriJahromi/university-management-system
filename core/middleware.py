from .models import ActivityLog

class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method == "POST" and request.user.is_authenticated:
            try:
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"POST {request.path}",
                )
            except Exception:
                pass

        return response
