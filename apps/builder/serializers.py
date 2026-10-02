from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from .models import Category, Choice, Form, Question


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


class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ["id", "label", "order"]

    def validate_label(self, value):
        if not value.strip():
            raise serializers.ValidationError("Choice label cannot be empty.")
        return value


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "id",
            "form",
            "type",
            "text",
            "is_required",
            "order",
            "config",
            "choices",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "form", "created_at", "updated_at"]

    def validate(self, attrs):
        question_type = attrs.get(
            "type",
            self.instance.type if self.instance else None,
        )
        choices = attrs.get("choices")
        config = attrs.get(
            "config",
            self.instance.config if self.instance else {},
        )

        choice_types = [Question.TYPE_SELECT, Question.TYPE_CHECKBOX]

        if question_type in choice_types:
            if choices is not None:
                if len(choices) < 2:
                    raise serializers.ValidationError(
                        {"choices": "At least two choices are required."}
                    )
            elif self.instance is None or self.instance.type not in choice_types:
                raise serializers.ValidationError(
                    {"choices": "At least two choices are required."}
                )
            elif self.instance.choices.filter(is_active=True).count() < 2:
                raise serializers.ValidationError(
                    {"choices": "At least two choices are required."}
                )
        elif choices:
            raise serializers.ValidationError(
                {"choices": "This question type does not support choices."}
            )

        if not isinstance(config, dict):
            raise serializers.ValidationError(
                {"config": "Config must be a JSON object."}
            )

        if question_type == Question.TYPE_TEXT:
            min_length = config.get("min_length", 0)
            max_length = config.get("max_length")

            if (
                not isinstance(min_length, int)
                or isinstance(min_length, bool)
                or min_length < 0
            ):
                raise serializers.ValidationError(
                    {"config": {"min_length": "Must be a non-negative integer."}}
                )

            if max_length is not None:
                if (
                    not isinstance(max_length, int)
                    or isinstance(max_length, bool)
                    or max_length < 0
                ):
                    raise serializers.ValidationError(
                        {"config": {"max_length": "Must be a non-negative integer."}}
                    )

                if min_length > max_length:
                    raise serializers.ValidationError(
                        {"config": "min_length cannot exceed max_length."}
                    )

        elif question_type == Question.TYPE_NUMBER:
            min_value = config.get("min")
            max_value = config.get("max")

            for key, value in (("min", min_value), ("max", max_value)):
                if value is not None:
                    try:
                        Decimal(str(value))
                    except (InvalidOperation, ValueError, TypeError):
                        raise serializers.ValidationError(
                            {"config": {key: "Must be a valid number."}}
                        )

            if min_value is not None and max_value is not None:
                if Decimal(str(min_value)) > Decimal(str(max_value)):
                    raise serializers.ValidationError(
                        {"config": "min cannot exceed max."}
                    )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        choices_data = validated_data.pop("choices", [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        choices_data = validated_data.pop("choices", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        choice_types = [Question.TYPE_SELECT, Question.TYPE_CHECKBOX]

        # When a question no longer supports choices, soft-delete its active choices.
        if instance.type not in choice_types:
            instance.choices.filter(is_active=True).update(is_active=False)
            return instance

        # No choices field in a PATCH request means existing choices remain unchanged.
        if choices_data is None:
            return instance

        existing_choices = list(
            Choice.objects.filter(question=instance, is_active=True)
        )
        existing_by_id = {choice.id: choice for choice in existing_choices}

        submitted_ids = [
            item["id"] for item in choices_data if "id" in item
        ]

        if len(submitted_ids) != len(set(submitted_ids)):
            raise serializers.ValidationError(
                {"choices": "Duplicate choice IDs are not allowed."}
            )

        for choice_id in submitted_ids:
            if choice_id not in existing_by_id:
                raise serializers.ValidationError(
                    {"choices": f"Invalid choice ID: {choice_id}"}
                )

        submitted_id_set = set(submitted_ids)

        # Omitted active choices are soft-deleted.
        for choice in existing_choices:
            if choice.id not in submitted_id_set:
                choice.is_active = False
                choice.save(update_fields=["is_active"])

        # Update existing choices or create new ones.
        for item in choices_data:
            choice_data = item.copy()
            choice_id = choice_data.pop("id", None)

            if choice_id is not None:
                choice = existing_by_id[choice_id]
                for attr, value in choice_data.items():
                    setattr(choice, attr, value)
                choice.save()
            else:
                Choice.objects.create(question=instance, **choice_data)

        return instance

    def validate_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a JSON object.")
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
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

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