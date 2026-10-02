from rest_framework import serializers

from apps.builder.models import Form
from apps.responses.serializers import SubmissionCreatedSerializer

from .models import Process, ProcessStep


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["id", "form", "order"]
        read_only_fields = ["order"]


class ProcessSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    steps = ProcessStepSerializer(many=True, read_only=True)

    class Meta:
        model = Process
        fields = [
            "id",
            "title",
            "description",
            "slug",
            "mode",
            "is_public",
            "category",
            "password",
            "steps",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def validate_category(self, category):
        if category is None:
            return category
        request = self.context["request"]
        if category.owner_id != request.user.id:
            raise serializers.ValidationError("Category does not belong to you.")
        return category

    def validate(self, attrs):
        # is_public defaults to the instance's current value on PATCH
        is_public = attrs.get(
            "is_public", getattr(self.instance, "is_public", False)
        )
        password = attrs.get("password")
        if not is_public and not password and not (
            self.instance and self.instance.password_hash
        ):
            raise serializers.ValidationError(
                {"password": "Private processes require a password."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        process = Process.objects.create(
            owner=self.context["request"].user, **validated_data
        )
        if password:
            process.set_password(password)
            process.save(update_fields=["password_hash"])
        return process

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        if validated_data.get("is_public"):
            instance.password_hash = None
        instance.save()
        return instance


class StepCreateSerializer(serializers.Serializer):
    form = serializers.PrimaryKeyRelatedField(queryset=Form.objects.all())

    def validate_form(self, form):
        request = self.context["request"]
        if form.owner_id != request.user.id:
            raise serializers.ValidationError("Form does not belong to you.")
        return form


class StepReorderSerializer(serializers.Serializer):
    order = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class RunStepSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    form = serializers.IntegerField()
    order = serializers.IntegerField()
    state = serializers.ChoiceField(choices=["done", "available", "locked"])


class RunStartSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    respondent_token = serializers.CharField()
    status = RunStepSerializer(many=True)


class RunStatusSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    completed_at = serializers.DateTimeField(allow_null=True)
    steps = RunStepSerializer(many=True)


class StepSubmitResultSerializer(SubmissionCreatedSerializer):
    """Same as the form-submit response, plus the run's completion time."""

    completed_at = serializers.DateTimeField(
        source="process_run.completed_at", read_only=True, allow_null=True
    )

    class Meta(SubmissionCreatedSerializer.Meta):
        fields = SubmissionCreatedSerializer.Meta.fields + ["completed_at"]
