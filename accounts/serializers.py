"""Registration contract (slice 2: reader accounts only; session shapes are schema-only)."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, allow_blank=False, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )


class RegistrationResponseSerializer(serializers.Serializer):
    """Schema-only shape of the registration 201 body (id + username)."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class LoginSerializer(serializers.Serializer):
    """Schema-only shape of the sign-in request (the view reads raw data)."""

    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class SessionStateSerializer(serializers.Serializer):
    """Schema-only shape of the sign-in state (mirrors session_state())."""

    authenticated = serializers.BooleanField()
    username = serializers.CharField(allow_null=True)
    is_librarian = serializers.BooleanField()
