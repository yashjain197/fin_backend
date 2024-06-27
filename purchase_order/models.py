from django.db import models

from accounts.models import User
from nopa.models import Purchaser, Supplier
from rfq.models import RFQ

# Create your models here.
# Make a different company table
class Projects(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    gst = models.CharField(max_length=15, unique=True, null=True, blank=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    contact_person_name = models.CharField(max_length=100, default="")
    contact_person_phone = models.CharField(max_length=15, default="")


    def __str__(self):
        return self.id
    
class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        (1, 'PO Created'),
        (2, 'PO Approved'),
        (3, 'NOPA Process Started'),
        (4, 'NOPA Completed'),
        (5, 'Completed'),
    )
    po_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    purchaser = models.ForeignKey(Purchaser, on_delete=models.CASCADE)
    project = models.ForeignKey(Projects, on_delete=models.CASCADE, null =True, blank=True)
    is_project = models.BooleanField(default=False)
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    payment_terms = models.TextField()
    delivery_terms = models.TextField()
    item_list = models.JSONField(null=False, blank=False) 
    remarks = models.TextField()
    #make a different table for made by approved by or same fileds in rfq po an nopa table
    made_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name = "made_by")
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="approved_by", null=True, blank=True)
    approved_by_date = models.DateField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_remaining= models.DecimalField(max_digits=10, decimal_places=2)
    #make different table for resale 
    is_resale = models.BooleanField(default=False)
    # make different table for pincode, state and city, address
    customer_delivery_address =  models.TextField(null=True, blank=True)
    #make different table
    contact_person_name = models.CharField(max_length=100, null=True, blank=True)
    contact_person_phone = models.CharField(max_length=15, null=True, blank=True)
    # same as RFQ
    revision = models.IntegerField(default=0)
    contract_no = models.CharField(max_length=50, null=True, blank=True)
    revision_remark = models.CharField(max_length=200, null=True, blank=True)
    #make different table for payment
    payment_history=models.JSONField(null=False, blank=False)   
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    #remoce this use status
    is_po_closed=models.BooleanField(default=False)
    #make tax percent
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    #same as RFQ
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    terms_and_conditions = models.CharField(max_length=500, null=True, blank=True)

    #make base model then abstarct it
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.id)

class POApproval(models.Model):
    requested_to = models.ForeignKey(User, on_delete=models.CASCADE)
    po_id = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)
    
