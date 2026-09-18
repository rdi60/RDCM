from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Patient
from .serializers import PatientMergeRequestSerializer, PatientMergeSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """Patient records API.

    GET /api/patients/?q=<name, phone or UHID> searches active patients —
    reception should search before registering, to catch duplicates before
    they happen (merge handles the ones that slip through).
    """

    serializer_class = PatientSerializer
    queryset = Patient.objects.select_related("registered_at_branch")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.filter(status=Patient.ACTIVE)
            q = self.request.query_params.get("q")
            if q:
                from django.db.models import Q
                qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(uhid__icontains=q))
        return qs

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        """Merge this (duplicate) patient into another. Body:
        {"target_patient_id": "<uuid>", "reason": "..."}"""
        source = self.get_object()
        serializer = PatientMergeRequestSerializer(
            data=request.data, context={"request": request, "source_patient": source},
        )
        serializer.is_valid(raise_exception=True)
        try:
            merge_record = serializer.save()
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return Response(PatientMergeSerializer(merge_record).data, status=status.HTTP_201_CREATED)
