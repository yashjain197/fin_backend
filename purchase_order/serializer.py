from rest_framework import serializers

from accounts.models import User
from rfq.models import RFQ
from .models import POApproval, Projects, PurchaseOrder

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class RFQSerializer(serializers.ModelSerializer):
    requested_by = UserSerializer()
    requested_to = UserSerializer()

    class Meta:
        model = RFQ
        fields = ['requested_by', 'requested_to', 'priority', 'attachment_list']

class PurchaseOrderSerializer(serializers.ModelSerializer):
    rfq_details = RFQSerializer(source='rfq', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class POApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = POApproval
        fields = ['id', 'requested_to', 'po_id', 'is_active', 'is_approved']

class ProjectsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = '__all__'