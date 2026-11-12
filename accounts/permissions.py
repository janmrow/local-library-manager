"""Staff permission (slice 2: librarian role)."""

from rest_framework.permissions import BasePermission


class IsLibrarian(BasePermission):
    """Allow only users in the Librarians group."""

    message = "Librarian access required."

    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.groups.filter(name="Librarians").exists()
