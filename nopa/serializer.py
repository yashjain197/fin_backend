from rest_framework import serializers
from .models import NOPA, NOPAApproval, PreNopa, Purchaser, Supplier


# class RFQSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = RFQ
#         fields = ['rfq_no', 'requested_by', 'requested_to', 'priority', 'project_name', 'description', 'material_category', 'item_list','resale_details' ,'attachments']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'address', 'state', 'city', 'gst', 'pincode']

class PurchaserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchaser
        fields = ['id', 'name', 'address', 'state', 'city', 'pincode', 'gst']

class NOPASerializer(serializers.ModelSerializer):
    class Meta:
        model = NOPA
        fields = '__all__'

class NOPAApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = NOPAApproval
        fields = ['id', 'requested_to', 'nopa_id', 'is_active', 'is_approved']

class PreNopaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreNopa
        fields = '__all__'