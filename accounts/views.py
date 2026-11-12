"""Session state view (slice 2, step 1: GET only)."""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(ensure_csrf_cookie, name="get")
class SessionView(APIView):
    """Return current sign-in state and set the CSRF cookie."""

    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if user.is_authenticated:
            return Response(
                {
                    "authenticated": True,
                    "username": user.username,
                    "is_librarian": user.groups.filter(name="Librarians").exists(),
                }
            )
        return Response({"authenticated": False, "username": None, "is_librarian": False})
