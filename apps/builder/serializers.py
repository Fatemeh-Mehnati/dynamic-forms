from rest_framework import serializers

from .models import Category, Form


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        request = self.context["request"]
        queryset = Category.objects.filter(owner=request.user, name=value)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "You already have a category with this name."
            )

        return value


class FormSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    response_url = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = [
            "id",
            "category",
            "title",
            "description",
            "slug",
            "is_public",
            "password",
            "response_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]

    def get_response_url(self, obj):
        return f"/api/v1/public/forms/{obj.slug}/submissions/"

    def validate_category(self, value):
        if value and value.owner != self.context["request"].user:
            raise serializers.ValidationError(
                "You can only use your own categories."
            )
        return value

    def validate(self, attrs):
        is_public = attrs.get(
            "is_public",
            self.instance.is_public if self.instance else False,
        )
        password = attrs.get("password")

        if not is_public and not password:
            if not self.instance or not self.instance.password_hash:
                raise serializers.ValidationError(
                    {"password": "A password is required for private forms."}
                )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        form = Form(**validated_data)
        if password:
            form.set_password(password)
        form.save()
        return form

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance