from rest_framework import serializers

from .models import Submission


class AnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    number = serializers.DecimalField(
        max_digits=20, decimal_places=6, required=False, allow_null=True
    )
    choices = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )


class SubmissionCreateSerializer(serializers.Serializer):
    """Only checks the shape of the input. Business rules live in services.py."""

    answers = AnswerInputSerializer(many=True)


class SubmissionCreatedSerializer(serializers.ModelSerializer):
    form = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "form", "submitted_at"]
