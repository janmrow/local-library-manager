from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from rest_framework import mixins, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accounts.permissions import IsLibrarian
from catalog.models import Book, BookCopy, normalize_inventory_code
from catalog.serializers import BookCreateSerializer, BookSerializer


class CopyCreateSerializer(serializers.Serializer):
    inventory_code = serializers.CharField(max_length=24)

    def validate_inventory_code(self, value):
        try:
            return normalize_inventory_code(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(str(exc.messages[0]))


class BookPagination(PageNumberPagination):
    page_size = 20


class BookViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
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

    def create(self, request, *args, **kwargs):
        SessionAuthentication().enforce_csrf(request)
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                book = input_serializer.save()
        except IntegrityError:
            return Response(
                {"code": "inventory_code_taken", "detail": "inventory_code already exists."},
                status=409,
            )
        annotated = self.get_queryset().get(pk=book.pk)
        return Response(BookSerializer(annotated).data, status=201)

    @action(detail=True, methods=["post"], url_path="copies")
    def add_copy(self, request, pk=None):
        SessionAuthentication().enforce_csrf(request)
        book = self.get_object()
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                copy = BookCopy.objects.create(
                    book=book, inventory_code=input_serializer.validated_data["inventory_code"]
                )
        except IntegrityError:
            return Response(
                {"code": "inventory_code_taken", "detail": "inventory_code already exists."},
                status=409,
            )
        return Response(
            {"id": copy.id, "inventory_code": copy.inventory_code, "book": book.pk},
            status=201,
        )
