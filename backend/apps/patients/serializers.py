from rest_framework import serializers

from apps.clinic.models import Branch

from .models import Patient, PatientMerge
from .services import merge_patients, register_patient


class PatientSerializer(serializers.ModelSerializer):
    registered_at_branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.filter(is_active=True))

    class Meta:
        model = Patient
        fields = [
            "id", "uhid", "registered_at_branch", "name", "date_of_birth", "gender",
            "phone", "email", "address", "referred_by", "status", "merged_into", "created_at",
        ]
        read_only_fields = ["id", "uhid", "status", "merged_into", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        branch = validated_data.pop("registered_at_branch")
        return register_patient(branch=branch, created_by=request.user, **validated_data)


class PatientMergeRequestSerializer(serializers.Serializer):
    target_patient_id = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    reason = serializers.CharField()

    def save(self, **kwargs):
        source = self.context["source_patient"]
        request = self.context["request"]
        return merge_patients(
            source=source,
            target=self.validated_data["target_patient_id"],
            reason=self.validated_data["reason"],
            merged_by=request.user,
        )


class PatientMergeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMerge
        fields = ["id", "source_patient", "target_patient", "reason", "merged_by", "merged_at"]
