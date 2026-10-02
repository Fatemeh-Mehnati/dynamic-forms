from rest_framework import serializers

from .models import ReportSchedule


class ReportScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSchedule
        fields = [
            "id",
            "frequency",
            "channel",
            "target",
            "is_active",
            "last_sent_at",
            "created_at",
        ]
        read_only_fields = ["id", "last_sent_at", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]

        if not request.user.is_staff:
            raise serializers.ValidationError(
                "Only staff users can manage report schedules."
            )

        return attrs