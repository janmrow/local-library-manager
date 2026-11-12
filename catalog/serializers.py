from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from catalog.models import Book, BookCopy, normalize_inventory_code


class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.IntegerField(read_only=True)
    total_copies = serializers.IntegerField(read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "author", "available_copies", "total_copies"]


class BookCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    author = serializers.CharField(max_length=255)
    inventory_code = serializers.CharField(max_length=24)

    def validate_inventory_code(self, value):
        return normalize_code(value)

    def create(self, validated_data):
        with transaction.atomic():
            book = Book.objects.create(
                title=validated_data["title"],
                author=validated_data["author"],
            )
            BookCopy.objects.create(book=book, inventory_code=validated_data["inventory_code"])
        return book


class CopyCreateSerializer(serializers.Serializer):
    inventory_code = serializers.CharField(max_length=24)

    def validate_inventory_code(self, value):
        return normalize_code(value)


def normalize_code(value):
    """Shared inventory_code validation for catalogue writes."""
    try:
        return normalize_inventory_code(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(str(exc.messages[0]))
