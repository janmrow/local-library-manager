"""Loan serializers (slice 3: validation contract only; writes live in operations)."""

from rest_framework import serializers

from catalog.serializers import normalize_code
from circulation.models import Loan


class LoanSerializer(serializers.ModelSerializer):
    inventory_code = serializers.CharField(source="copy.inventory_code", read_only=True)
    book = serializers.IntegerField(source="copy.book_id", read_only=True)

    class Meta:
        model = Loan
        fields = ["id", "inventory_code", "book", "borrowed_at", "returned_at"]


class CheckoutSerializer(serializers.Serializer):
    # No max_length: length is validated on the trimmed input (see normalize_code).
    inventory_code = serializers.CharField()

    def validate_inventory_code(self, value):
        return normalize_code(value)
