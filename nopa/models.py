from django.db import models
from django.utils.timezone import now

from accounts.models import User
#make master app, city, state supplier (less CRUD operations)
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    gst = models.CharField(max_length=15, unique=True, null=True, blank=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name

class Purchaser(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    gst = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.name

#Payemnt table for NOPA, for item list, pending amount etc and then we don't need prenopa table
class PreNopa(models.Model):
     STATUS_CHOICES = (
        (1, 'NOPA Process Started'),
        (2, 'NOPA Completed'),
    )
     po = models.ForeignKey('purchase_order.PurchaseOrder', on_delete=models.CASCADE)
     pre_nopa_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
     item_list = models.JSONField(null=False, blank=False) 
     payment_history=models.JSONField(null=False, blank=False) 
     sub_total = models.DecimalField(max_digits=10, decimal_places=2)
     tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
     amount_remaining= models.DecimalField(max_digits=10, decimal_places=2)
     tds= models.DecimalField(max_digits=6, decimal_places=2, default=0)
     tds_amount= models.DecimalField(max_digits=10, decimal_places=2, default=0)
     esi= models.DecimalField(max_digits=6, decimal_places=2, default=0)
     esi_amount= models.DecimalField(max_digits=10, decimal_places=2, default=0)
     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
     prepared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pre_nopa_prepared_by', null=True, blank=True)
     is_nopa_closed = models.BooleanField(default=False)
     status = models.IntegerField(choices=STATUS_CHOICES, default=1)
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)
     def __str__(self):
        return str(self.id)

class NOPA(models.Model):
    STATUS_CHOICES = (
        (1, 'Generated'),
        (2, 'Approved'),
        (3, 'Paid'),
    )
    pre_nopa = models.ForeignKey(PreNopa, on_delete=models.CASCADE)
    payment_history = models.JSONField(null=True, blank=True)
    nopa_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    invoice_no = models.CharField(max_length=50)
    amount_to_be_paid_on_date = models.DateField()
    amount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    prepared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_prepared_by', null=True, blank=True)
    checked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_checked_by', null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_reviewed_by', null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_approved_by', null=True, blank=True)
    checked_by_accountant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_checked_by_accountant', null=True, blank=True)
    approved_by_accountant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_approved_by_accountant', null=True, blank=True)
    end_customer_details = models.JSONField(null=True, blank=True)
    mode_of_payment=models.CharField(null=True, blank=True)
    amount_paid_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nopa_amount_paid_by', null=True, blank=True)
    amount_paid_from=models.CharField(null=True, blank=True)
    attachments = models.BooleanField(default=False)
    attachment_list = models.JSONField(null=True,blank=True)
    remarks = models.CharField(max_length=100, null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    utr_no = models.CharField(max_length=300, null=True, blank=True, default="")
    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
    
class NOPAApproval(models.Model):
    requested_to = models.ForeignKey(User, on_delete=models.CASCADE)
    nopa_id = models.ForeignKey(NOPA, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)
