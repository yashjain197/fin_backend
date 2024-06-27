from django.db import models
from accounts.models import User
from nopa.models import Purchaser

# Create your models here.

class  RFQ(models.Model):
    PRIORITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Normal', 'Normal'),
        ('Low', 'Low'),
    ]
    STATUS_CHOICES = (
        (1, 'RFQ Created'),
        (2, 'RFQ Approved'),
        (3, 'PO Process Started'),
        (4, 'PO Process Completed'),
        (5, 'NOPA Process Started'),
        (6, 'NOPA Process Completed'),
        (7, 'Completed'),
        (8, 'Rejected'),
    )
    # history table for all rfq
    rfq_no = models.CharField(max_length=50,unique=True,null=True, blank=True)
    purchaser = models.ForeignKey(Purchaser, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_rfqs')
    requested_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_rfqs')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    project_name = models.CharField(max_length=100, default='', null=True, blank=True)
    description = models.TextField(default='')
    #material category table
    material_category = models.CharField(max_length=100)
    resale_details = models.JSONField(null=True, blank=True) 
    item_list = models.JSONField(null=False, blank=False)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rfq_approved_by", null=True, blank=True)
    approved_by_date = models.DateField(null=True, blank=True)
    is_manager_approval = models.BooleanField(default=False)
    approved_by_manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="manager_approved_by", null=True, blank=True)
    approved_by_manager_date =  models.DateField(null=True, blank=True)
    attachments = models.BooleanField(default=False)
    attachment_list = models.JSONField(null=True,blank=True)
    #RFQ Revision tabel
    revision = models.IntegerField(default=0, null=True, blank=True)
    is_po_generated = models.BooleanField(default=False)
    is_rfq_rejected = models.BooleanField(default=False)
    rejected_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rejected_by", null=True, blank=True)
    is_rfq_closed = models.BooleanField(default=False)
    is_only_rfq = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_status_display(self):
        return dict(RFQ.STATUS_CHOICES)[self.status]
    
    def __str__(self):
        return str(self.id)
#2 tables for approval
# One will be the template of the approval
# Approval done by (save designation role)
class RFQApproval(models.Model):
    requested_to = models.ForeignKey(User, on_delete=models.CASCADE)
    rfq_id = models.ForeignKey(RFQ, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)