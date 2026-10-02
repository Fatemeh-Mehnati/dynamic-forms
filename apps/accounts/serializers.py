from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from .models import OTPCode, User


class OTPRequestSerializer(serializers.Serializer):
    target = serializers.CharField(max_length=254)
    purpose = serializers.ChoiceField(choices=OTPCode.Purpose.choices)


class OTPVerifySerializer(OTPRequestSerializer):
    code = serializers.RegexField(r"^\d+$", max_length=10)
    username = serializers.CharField(
        max_length=150, required=False, validators=[UnicodeUsernameValidator()]
    )

    def validate(self, attrs):
        if attrs["purpose"] == OTPCode.Purpose.REGISTER:
            username = attrs.get("username")
            if not username:
                raise serializers.ValidationError({"username": "Username is required to register."})
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "This username is taken."})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "phone"]

class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone"]
        read_only_fields = ["id", "email", "phone"]


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False)