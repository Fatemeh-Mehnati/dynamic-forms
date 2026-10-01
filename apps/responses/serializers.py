from rest_framework import serializers

from .models import Answer, Submission


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


class AnswerDetailSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)
    type = serializers.CharField(source="question.type", read_only=True)
    choices = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "question",
            "question_text",
            "type",
            "text_value",
            "number_value",
            "choices",
        ]

    def get_choices(self, answer):
        return [
            {"id": sc.choice_id, "label": sc.choice.label}
            for sc in answer.selected_choices.all()
        ]


class SubmissionListSerializer(serializers.ModelSerializer):
    """Used for the paginated list endpoint: no answers, just metadata."""

    class Meta:
        model = Submission
        fields = ["id", "user", "process_run", "submitted_at"]


class SubmissionDetailSerializer(serializers.ModelSerializer):
    """Used for the single-submission endpoint: includes every answer."""

    answers = AnswerDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "user", "process_run", "submitted_at", "answers"]
