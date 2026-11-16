from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from catalog.models import Book, BookCopy, normalize_inventory_code


def normalize_code(value):
    """Shared inventory_code validation for catalogue writes."""
    try:
        return normalize_inventory_code(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(str(exc.messages[0]))


class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.IntegerField(read_only=True)
    total_copies = serializers.IntegerField(read_only=True)
    available_codes = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "available_copies",
            "total_copies",
            "available_codes",
        ]

    def get_available_codes(self, obj):
        return [copy.inventory_code for copy in obj.copies.all() if not copy.open_loans]


class BookCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    author = serializers.CharField(max_length=255)
    # No max_length: length is validated on the trimmed input (see normalize_code).
    inventory_code = serializers.CharField()

    def validate_inventory_code(self, value):
        return normalize_code(value)

    def create(self, validated_data):
        # Atomicity is owned by the view (BookViewSet.create wraps this call);
        # serializers validate only.
        book = Book.objects.create(
            title=validated_data["title"],
            author=validated_data["author"],
        )
        BookCopy.objects.create(book=book, inventory_code=validated_data["inventory_code"])
        return book


class BookCopyResponseSerializer(serializers.Serializer):
    """Schema-only shape of the add-copy response (id, code, book)."""

    id = serializers.IntegerField(read_only=True)
    inventory_code = serializers.CharField(read_only=True)
    book = serializers.IntegerField(read_only=True)


class CopyCreateSerializer(serializers.Serializer):
    # No max_length: length is validated on the trimmed input (see normalize_code).
    inventory_code = serializers.CharField()

    def validate_inventory_code(self, value):
        return normalize_code(value)
