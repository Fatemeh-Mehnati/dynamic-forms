from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Process, ProcessStep
from .serializers import (
    ProcessSerializer,
    ProcessStepSerializer,
    StepCreateSerializer,
    StepReorderSerializer,
)


class ProcessListCreateView(generics.ListCreateAPIView):
    """List the user's own processes (filter: category, search) and create new ones."""

    serializer_class = ProcessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Process.objects.filter(owner=self.request.user).order_by("-created_at")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        return qs


class ProcessDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, partially update, or delete a process. Owner only."""

    serializer_class = ProcessSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        return Process.objects.filter(owner=self.request.user)


class ProcessStepCreateView(APIView):
    """Append a step to the end of a process. Owner only; form must be the user's own."""

    permission_classes = [IsAuthenticated]

    def get_process(self):
        return get_object_or_404(
            Process, pk=self.kwargs["process_id"], owner=self.request.user
        )

    @extend_schema(
        request=StepCreateSerializer, responses={201: ProcessStepSerializer}
    )
    def post(self, request, process_id):
        process = self.get_process()
        serializer = StepCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        last_order = process.steps.count()
        step = ProcessStep.objects.create(
            process=process,
            form=serializer.validated_data["form"],
            order=last_order + 1,
        )
        return Response(
            ProcessStepSerializer(step).data, status=status.HTTP_201_CREATED
        )


class ProcessStepDeleteView(APIView):
    """Remove one step from a process. Owner only."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, process_id, step_id):
        step = get_object_or_404(
            ProcessStep, pk=step_id, process_id=process_id, process__owner=request.user
        )
        step.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProcessStepReorderView(APIView):
    """Reassign step order from a full list of step ids (new order, first to last)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=StepReorderSerializer, responses={200: ProcessStepSerializer(many=True)}
    )
    def post(self, request, process_id):
        process = get_object_or_404(Process, pk=process_id, owner=request.user)
        serializer = StepReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        step_ids = serializer.validated_data["order"]

        steps = {step.id: step for step in process.steps.all()}
        if set(step_ids) != set(steps.keys()):
            raise ValidationError(
                {"order": "Must list exactly the process's current steps."}
            )

        with transaction.atomic():
            # The (process, order) constraint is DEFERRED, so this works
            # even while two steps briefly share an order value.
            for position, step_id in enumerate(step_ids, start=1):
                ProcessStep.objects.filter(pk=step_id).update(order=position)

        ordered = ProcessStep.objects.filter(process=process).order_by("order")
        return Response(ProcessStepSerializer(ordered, many=True).data)
