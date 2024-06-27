from django.contrib import admin

from .models import Purchaser, Supplier

admin.site.register(Supplier)
admin.site.register(Purchaser)