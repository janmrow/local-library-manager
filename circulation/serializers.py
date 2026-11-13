"""Loan serializers (slice 3: checkout keeps its write in an atomic block)."""

from django.db import transaction
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
    inventory_code = serializers.CharField(max_length=24)

    def validate_inventory_code(self, value):
        return normalize_code(value)

    def create(self, validated_data):
        with transaction.atomic():
            return Loan.objects.create(
                copy=validated_data["copy"],
                reader=validated_data["reader"],
            )
