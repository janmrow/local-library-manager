"""Session and registration views (slice 2, step 2: registration added)."""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import RegistrationSerializer


def enforce_csrf_without_session(request) -> None:
    """Enforce CSRF even for logged-out POSTs (DRF skips it when anonymous)."""
    SessionAuthentication().enforce_csrf(request)


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


class RegistrationView(APIView):
    """Create a reader account; CSRF required even without a session."""

    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf_without_session(request)
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username}, status=201)
