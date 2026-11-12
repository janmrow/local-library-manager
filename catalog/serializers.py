from django.core.exceptions import ValidationError as DjangoValidationError
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
        try:
            return normalize_inventory_code(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(str(exc.messages[0]))

    def create(self, validated_data):
        book = Book.objects.create(
            title=validated_data["title"],
            author=validated_data["author"],
        )
        BookCopy.objects.create(book=book, inventory_code=validated_data["inventory_code"])
        return book
