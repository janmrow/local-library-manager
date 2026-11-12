"""Session and registration views (slice 2: accounts and session)."""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import RegistrationSerializer


def enforce_csrf_without_session(request) -> None:
    """Enforce CSRF even for logged-out POSTs (DRF skips it when anonymous)."""
    SessionAuthentication().enforce_csrf(request)


def session_state(user) -> dict:
    if user.is_authenticated:
        return {
            "authenticated": True,
            "username": user.username,
            "is_librarian": user.groups.filter(name="Librarians").exists(),
        }
    return {"authenticated": False, "username": None, "is_librarian": False}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    """GET state, POST sign-in, DELETE sign-out; CSRF required on writes."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(session_state(request.user))

    def post(self, request):
        enforce_csrf_without_session(request)
        data = request.data if isinstance(request.data, dict) else {}
        username = data.get("username", "")
        password = data.get("password", "")
        if not username or not password:
            raise serializers.ValidationError("Invalid credentials.")
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        login(request, user)
        return Response(session_state(user))

    def delete(self, request):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        logout(request)
        return Response(status=204)


class RegistrationView(APIView):
    """Create a reader account; CSRF required even without a session."""

    permission_classes = [AllowAny]

    def post(self, request):
        enforce_csrf_without_session(request)
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"id": user.id, "username": user.username}, status=201)
