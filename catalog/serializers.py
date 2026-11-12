from rest_framework import serializers

from catalog.models import Book


class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.IntegerField(read_only=True)
    total_copies = serializers.IntegerField(read_only=True)

    class Meta:
        model = Book
        fields = ["id", "title", "author", "available_copies", "total_copies"]
