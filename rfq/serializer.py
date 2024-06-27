from rest_framework import serializers
from .models import RFQ, RFQApproval


class RFQSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQ
        fields = ['requested_by', 'requested_to', 'priority', 'project_name', 'description', 'material_category', 'item_list','resale_details' ,'attachments', 'purchaser']

class RFQItemListUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQ
        fields = ['item_list', 'is_po_generated', 'is_rfq_closed']

class RFQApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQApproval
        fields = ['id', 'requested_to', 'rfq_id', 'is_active', 'is_approved']