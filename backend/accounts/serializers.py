from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password"]

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        # Django's built-in rules: minimum length, not too common, not all digits.
        validate_password(value)
        return value

    def create(self, validated_data):
        # Django's User still needs a unique username, so we reuse the email.
        # create_user() hashes the password (PBKDF2 by default); it is never stored as plain text.
        return User.objects.create_user(username=validated_data["email"], **validated_data)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
