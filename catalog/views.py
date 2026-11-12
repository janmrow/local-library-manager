from django.db.models import Count, F, Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from catalog.models import Book
from catalog.serializers import BookSerializer


class BookPagination(PageNumberPagination):
    page_size = 20


class BookViewSet(ReadOnlyModelViewSet):
    """Public catalogue browse (slice 1: list + retrieve only)."""

    serializer_class = BookSerializer
    permission_classes = [AllowAny]
    pagination_class = BookPagination

    def get_queryset(self):
        queryset = (
            Book.objects.annotate(
                total_copies=Count("copies", distinct=True),
                open_loans=Count(
                    "copies__loan",
                    filter=Q(copies__loan__returned_at__isnull=True),
                    distinct=True,
                ),
            )
            .annotate(available_copies=F("total_copies") - F("open_loans"))
            .order_by("title", "id")
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(title__icontains=q) | Q(author__icontains=q))
        return queryset
