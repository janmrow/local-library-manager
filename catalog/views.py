from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accounts.permissions import IsLibrarian
from accounts.views import enforce_csrf_without_session
from catalog.models import Book, BookCopy
from catalog.serializers import BookCreateSerializer, BookSerializer, CopyCreateSerializer


def inventory_code_taken():
    return Response(
        {"code": "inventory_code_taken", "detail": "inventory_code already exists."},
        status=409,
    )


class BookPagination(PageNumberPagination):
    page_size = 20


class BookViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Public browse plus librarian create (slice 2: no update/delete)."""

    pagination_class = BookPagination

    def get_permissions(self):
        if self.action in ("create", "add_copy"):
            return [IsLibrarian()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return BookCreateSerializer
        if self.action == "add_copy":
            return CopyCreateSerializer
        return BookSerializer

    def annotated_books(self):
        return (
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

    def get_queryset(self):
        queryset = self.annotated_books()
        if self.action == "list":
            q = self.request.query_params.get("q", "").strip()
            if q:
                queryset = queryset.filter(Q(title__icontains=q) | Q(author__icontains=q))
        return queryset

    def create(self, request, *args, **kwargs):
        enforce_csrf_without_session(request)
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                book = input_serializer.save()
        except IntegrityError:
            return inventory_code_taken()
        annotated = self.annotated_books().get(pk=book.pk)
        return Response(BookSerializer(annotated).data, status=201)

    @action(detail=True, methods=["post"], url_path="copies")
    def add_copy(self, request, pk=None):
        enforce_csrf_without_session(request)
        book = self.get_object()
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                copy = BookCopy.objects.create(
                    book=book, inventory_code=input_serializer.validated_data["inventory_code"]
                )
        except IntegrityError:
            return inventory_code_taken()
        return Response(
            {"id": copy.id, "inventory_code": copy.inventory_code, "book": book.pk},
            status=201,
        )
