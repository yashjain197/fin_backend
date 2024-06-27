from datetime import datetime
import threading
from django.shortcuts import render
from django.core.paginator import Paginator
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.core.mail import send_mail
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from nopa_backend import settings
from rfq.models import RFQ

from .models import NOPA, NOPAApproval, PreNopa, Purchaser, Supplier
from accounts.models import User
from purchase_order.models import PurchaseOrder
from rfq.utils import getFormattedDate
from .utils import generate_nopa_no, generate_pre_nopa_no, get_nopa_status_display, get_pre_nopa_status_display

from openpyxl import Workbook
from io import BytesIO
from .serializer import NOPAApprovalSerializer, NOPASerializer, PreNopaSerializer, PurchaserSerializer, SupplierSerializer

from weasyprint import HTML

def generate_nopa_pdf(id):
    nopa = NOPA.objects.get(id=id)
 
    total_quantity = 0
    for item in nopa.pre_nopa.item_list:
       total_quantity += float(item["quantity"])
    date = getFormattedDate(nopa.created_at)
    if nopa.pre_nopa.po.is_resale:
        context = {
                "nopa_no": nopa.nopa_no,
                "date": date,
                "rfq_no": "",
                "rfq_date":"",
                "rfq_department": "",
                "po_no": nopa.pre_nopa.po.po_no,
                "po_date": getFormattedDate(nopa.pre_nopa.po.created_at),
                "po_made_by": nopa.pre_nopa.po.made_by.first_name + " " + nopa.pre_nopa.po.made_by.last_name,
                "pi_no":nopa.invoice_no,
                "subtotal": nopa.pre_nopa.sub_total,
                "tax_amount": nopa.pre_nopa.tax_amount,
                "total_amount": nopa.pre_nopa.total_amount,
                "payment_terms": nopa.pre_nopa.po.payment_terms,
                "item_list" :  nopa.pre_nopa.item_list,
                "total_quantity": total_quantity,
                "supplier_name": nopa.pre_nopa.po.supplier.name,
                "supplier_gst": nopa.pre_nopa.po.supplier.gst,
                "payment_history": nopa.pre_nopa.payment_history,
                "purchaser": nopa.pre_nopa.po.purchaser.id,
                "purchaser_name": nopa.pre_nopa.po.purchaser.name, 
                "amount_percent_to_be_paid": nopa.amount_percent,
                "total_amount_to_be_paid": nopa.amount_paid,
                "amount_to_be_paid_on_date": nopa.amount_to_be_paid_on_date,
                "amount_outstanding": nopa.pre_nopa.amount_remaining
                }
    else:
        context = {
                    "nopa_no": nopa.nopa_no,
                    "date": date,
                    "rfq_no": nopa.pre_nopa.po.rfq.rfq_no,
                    "rfq_date": getFormattedDate(nopa.pre_nopa.po.rfq.created_at),
                    "rfq_department": nopa.pre_nopa.po.rfq.requested_by.department,
                    "po_no": nopa.pre_nopa.po.po_no,
                    "po_date": getFormattedDate(nopa.pre_nopa.po.created_at),
                    "po_made_by": nopa.pre_nopa.po.made_by.first_name.title() + " " + nopa.pre_nopa.po.made_by.last_name.title(),
                    "pi_no":nopa.invoice_no,
                    "subtotal": nopa.pre_nopa.po.sub_total,
                    "tax_amount": nopa.pre_nopa.po.tax_amount,
                    "total_amount": nopa.pre_nopa.po.total_amount,
                    "project_name": nopa.pre_nopa.po.rfq.project_name,
                    "description": nopa.pre_nopa.po.rfq.description,
                    "payment_terms": nopa.pre_nopa.po.payment_terms,
                    "item_list" :  nopa.pre_nopa.item_list,
                    "total_quantity": total_quantity,
                    "purchaser": nopa.pre_nopa.po.purchaser.id, 
                    "purchaser_name": nopa.pre_nopa.po.purchaser.name, 
                    "supplier_name": nopa.pre_nopa.po.supplier.name,
                    "supplier_gst": nopa.pre_nopa.po.supplier.gst,
                    "payment_history": nopa.payment_history,
                    "amount_percent_to_be_paid": nopa.amount_percent,
                    "total_amount_to_be_paid": nopa.amount_paid,
                    "amount_to_be_paid_on_date": nopa.amount_to_be_paid_on_date,
                    "amount_outstanding": nopa.pre_nopa.amount_remaining
                    }
        
        if nopa.pre_nopa.po.rfq.approved_by is not None:
            context["rfq_approved_by"] = nopa.pre_nopa.po.rfq.approved_by.first_name.title() + " " + nopa.pre_nopa.po.rfq.approved_by.last_name.title() 
        
        if nopa.pre_nopa.po.rfq.approved_by_manager is not None:
            context["rfq_approved_by_manager"] = nopa.pre_nopa.po.rfq.approved_by_manager.first_name.title() + " " + nopa.pre_nopa.po.rfq.approved_by_manager.last_name.title() 
    
    if nopa.pre_nopa.po.approved_by is not None:
        context["po_approved_by"] = nopa.pre_nopa.po.approved_by.first_name.title()+ " " + nopa.pre_nopa.po.approved_by.last_name.title() 
        print(context["po_approved_by"])
    if nopa.remarks is not None:
        context["remarks"] = nopa.remarks

    if nopa.prepared_by:
        context["requisition_prepared_by"] = nopa.prepared_by.first_name.title() + " " + nopa.prepared_by.last_name.title()

    if nopa.checked_by:
        context["requisition_checked_by"] = nopa.checked_by.first_name.title() + " " + nopa.checked_by.last_name.title()

    if nopa.reviewed_by:
        context["requisition_reviewed_by"] = nopa.reviewed_by.first_name.title() + " " + nopa.reviewed_by.last_name.title()

    if nopa.approved_by:
        context["requisition_approved_by"] = nopa.approved_by.first_name.title() + " " + nopa.approved_by.last_name.title()

    if nopa.checked_by_accountant:
        context["accounts_checked_by"] = nopa.checked_by_accountant.first_name.title() + " " + nopa.checked_by_accountant.last_name.title()

    if nopa.approved_by_accountant:
        context["accounts_approved_by"] = nopa.approved_by_accountant.first_name.title() + " " + nopa.approved_by_accountant.last_name.title()

    if nopa.amount_paid_by:
        context["amount_paid_by"] = nopa.amount_paid_by.first_name.title() + " " + nopa.amount_paid_by.last_name.title()

    if nopa.amount_paid_by:
        context["amount_paid_from"] = nopa.amount_paid_from
    
    
    context["tds_amount"] = nopa.pre_nopa.tds_amount
    
    context["esi_amount"] = nopa.pre_nopa.esi_amount

    if nopa.pre_nopa.po.is_resale:
        context["resale_details"] = nopa.end_customer_details
        context["customer_dilivery_address"] = nopa.pre_nopa.po.customer_delivery_address
        html_string1 = get_template('nopa2.html').render(context)
        pdf_file = HTML(string=html_string1).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="nopa.pdf"'
        return response

    html_string1 = get_template('nopa.html').render(context)
    pdf_file = HTML(string=html_string1).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="nopa.pdf"'
    return response

class VendorView(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request):
        print(request.data)
        serializer = SupplierSerializer(data=request.data)
        if serializer.is_valid():
            print("data saved")
            serializer.save()  # Save the data to the database
            output = {
                "status": 201,
                "success": True,
                "message": "data saved successfully"
            }
            return Response(output, status=status.HTTP_201_CREATED)
        return Response({
                "status": 400,
                "success": False,
                "error": serializer.errors
            }, status=status.HTTP_200_OK)
    
    def get(self, request):
        query = request.query_params.get("query")
        id = request.query_params.get("id")
        suppliers = []
        if query is None and id is None:
            suppliers = Supplier.objects.all()
            suppliers = suppliers.order_by('name') 
        elif id is None:
            suppliers = Supplier.objects.filter(name__icontains=query)
            suppliers = suppliers.order_by('name') 
        
        if id is not None:
            try:
                suppliers = Supplier.objects.get(id = id)
            except Exception as e:
                return Response({
                    "status": 200,
                    "success": False,
                    "message": "Vendor Not Found",
                    "error" : e
                })
        
        
        data = [{ 'id': supplier.id,
                'name': supplier.name,
                'address': supplier.address,
                'state': supplier.state,
                'city': supplier.city,
                'gst': supplier.gst,
                'pincode': supplier.pincode} for supplier in suppliers]
        
        return Response({
            "status": 200,
            "success": True,
            "message": "successfull GET request",
            "data": data
        })
    
    def put(self, request):
        supplier_id = request.query_params.get('id')
        try:
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            return Response(
                {
                'status': 200,
                'success': False,
                "message" : "something went wrong",
                'error': 'Supplier not found'
                }, status=200)

        serializer = SupplierSerializer(supplier, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "Data Saved successfully"
            }, status=status.HTTP_200_OK)
        
        return Response(
                {
                'status': 200,
                'success': False,
                "message" : "something went wrong",
                'error': serializer.errors
                }, status=200)
        
class PurchaserView(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request):
        serializer = PurchaserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the data to the database
            output = {
                "status": 201,
                "success": True,
                "message": "data saved successfully"
            }
            return Response(output, status=status.HTTP_201_CREATED)
        return Response({
                "status": 400,
                "success": False,
                "error": serializer.errors
            }, status=status.HTTP_200_OK)
    
    def get(self, request):
        query = request.query_params.get("query")
        if query is None:
            purchaser = Purchaser.objects.all()
        else:
            purchaser = Purchaser.objects.filter(name__icontains=query)
        
        purchaser = purchaser.order_by('name')
        
        data = [{ 'id': purchaser.id,
                'name': purchaser.name,
                'address': purchaser.address,
                'state': purchaser.state,
                'city': purchaser.city,
                'gst': purchaser.gst,
                'pincode': purchaser.pincode} for purchaser in purchaser]
        
        return Response({
            "status": 200,
            "success": True,
            "message": "successfull GET request",
            "data": data
        })

class GeneratePreNopa(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request):
        data = request.data
        po = PurchaseOrder.objects.get(id=data["po_id"])
        data["po"] = po.id
        data["prepared_by"] = request.user.id
        data["payment_history"] = []

        item_list = data["item_list"]
        print(data["item_list"])
        total_amount = 0
        tax_amount = 0
        sub_total = 0
        for item in item_list:
            total_amount += item["total_amount"]
            sub_total += item["sub_total"]
            tax_amount += item["tax_amount"]
            for po_item in po.item_list:
                if item["id"] == po_item["id"]:
                    po_item["is_nopa_generated"] = True
        is_po_closed = True   
        for item in po.item_list:
            if item["is_nopa_generated"] == False:
                is_po_closed = False
        
        if is_po_closed:
            po.is_po_closed = True
        
        po.save()
        serializer = PreNopaSerializer(data = data)

        if data.get("tds"):
            sub_total = sub_total - data["tds_amount"]
        if data.get("esi"):
            sub_total = sub_total - data["esi_amount"]

        total_amount = sub_total + tax_amount
        data["total_amount"] = total_amount
        data["tax_amount"] = tax_amount
        data["sub_total"] = sub_total
        data["amount_remaining"] = sub_total

        if serializer.is_valid():
            preNopa = serializer.save()
            preNopa = PreNopa.objects.get(id=preNopa.id)
            preNopa.pre_nopa_no = generate_pre_nopa_no(preNopa.id, preNopa.po.purchaser.id)
            # preNopa.po.status = 3
            po = PurchaseOrder.objects.get(id = po.id)
            po.status = 3
            if not preNopa.po.is_resale:
                rfq = RFQ.objects.get(id = preNopa.po.rfq.id)
                rfq.status = 5
                rfq.save()
                # preNopa.po.rfq.status = 5
            preNopa.save()
            po.save()
            return Response({
                "status": 201,
                "success": True,
                "message": "successfully saved data",
                "id": preNopa.id
            })
        
        return Response({
                "status": 400,
                "success": False,
                "message": "some problem occoured in saving the data",
                "error": serializer.errors
                })

class GenerateNOPA(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request):
        data = request.data
        # nopa_no=generate_nopa_no()
        preNoap = PreNopa.objects.get(id=data["pre_nopa_id"])
        if preNoap.amount_remaining == 0:
            return Response({
                "success": False,
                "status": 400,
                "message": "no outstanding amount is remaining",
            })
        payment_history = preNoap.payment_history
        data["payment_history"] = payment_history.copy()
        data["prepared_by"] = request.user.id
        if preNoap.po.is_resale:
            data["checked_by"] = request.user.id
        # data["nopa_no"] = nopa_no
        data["pre_nopa"] = preNoap.id
        if data.get('attachment_list') is not None:
            data['attachments'] = True
        else:
            data['attachments'] = False
        if(float(preNoap.amount_remaining) < data["amount_paid"]):
             return Response({
                "success": False,
                "status": 400,
                "message": "Amount exceeding"
            })
        
        if(float(preNoap.amount_remaining) - data["amount_paid"] == 0):
            data["amount_paid"] += float(preNoap.tax_amount)
            preNoap.amount_remaining += preNoap.tax_amount
            preNoap.is_nopa_closed = True
            preNoap.status = 2
        preNoap.amount_remaining =  float(preNoap.amount_remaining) - data["amount_paid"]
        preNoap.po.amount_remaining = float(preNoap.po.amount_remaining) - data["amount_paid"]
        if preNoap.po.amount_remaining == 0:
            preNoap.po.is_po_closed = True
        serializer = NOPASerializer(data=data)
        if serializer.is_valid():
            nopa = serializer.save()
            nopa = NOPA.objects.get(id=nopa.id)
            count = NOPA.objects.filter(pre_nopa = preNoap.id).count()
            nopa.nopa_no = generate_nopa_no(preNoap.pre_nopa_no, count)
            updated_payment_history_data = {
                "nopa_no":  nopa.nopa_no,
                "amount_percent": data["amount_percent"],
                "amount_paid": data["amount_paid"],
                "date": data["amount_to_be_paid_on_date"],
                "mode_of_payment": data["mode_of_payment"]
                }
            nopa.pre_nopa.status = 1
            nopa.status = 1
            payment_history.append(updated_payment_history_data)
            preNoap.payment_history = payment_history          

            #sending it for checking
            if not nopa.pre_nopa.po.is_resale:
                user = User.objects.get(id = nopa.pre_nopa.po.rfq.requested_by.id)
                approval_data = {
                    "requested_to": user.id,
                    "nopa_id": nopa.id
                }
                approvalSerilizer = NOPAApprovalSerializer(data = approval_data)
                if approvalSerilizer.is_valid():
                    approvalSerilizer.save()
                    
            else:
                user = User.objects.get(id = data["approval_to"])
                if user.role == "Admin":
                    nopa.checked_by =  User.objects.get(id = request.user.id)
                approval_data = {
                    "requested_to": user.id,
                    "nopa_id": nopa.id
                }
                approvalSerilizer = NOPAApprovalSerializer(data = approval_data)
                if approvalSerilizer.is_valid():
                    approvalSerilizer.save()

            email_from = settings.EMAIL_HOST_USER
            email_to = user.email
            subject = "Reminder Mail"
            message = f"An NOPA with the number {nopa.nopa_no} has been created and is awaiting your approval. Please review it at your earliest convenience."
            recipient_list = [email_to,]
            threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()
            preNoap.save()
            nopa.save()
            return generate_nopa_pdf(nopa.id)
        print(serializer.errors)
        return Response({
                "success": False,
                "status": 400,
                "message": "unsuccessful GET request",
                "error": serializer.errors
            })
 
class FetchAllNOPA(APIView):
    permission_classes= (IsAuthenticated, )
    def get(self, request):
        id =  request.query_params.get("pre_nopa_id")
        supplier = request.query_params.get("supplier")
        page = request.query_params.get("page")
        query = request.query_params.get("query")
        status2 = request.query_params.get("status")
        invoice = request.query_params.get("invoice_no")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        utr_no = request.query_params.get("utr_no")
        
        amount_remaining = 0
        if request.user.role == 'Admin' or id is None:
             queryset = NOPA.objects.all()
        else:
            queryset = NOPA.objects.filter(pre_nopa = id)
            pre_nopa = PreNopa.objects.get(id = id)
            amount_remaining = pre_nopa.amount_remaining

        if from_date and to_date is not None:
            queryset = queryset.filter(created_at__date__range=[from_date, to_date])
        elif from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        elif to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
            
        if supplier:
            queryset = queryset.filter(pre_nopa__po__supplier = supplier)

        if status2:
            queryset = queryset.filter(status__icontains = status2)
        
        if invoice:
            queryset = queryset.filter(invoice_no__icontains = invoice)

        if utr_no is not None:
            if utr_no.lower() == 'false':
                queryset = queryset.filter(utr_no='')
            elif utr_no.lower() == 'true':
                queryset = queryset.exclude(utr_no='')

        if query:
        # Build your Q object for searching across multiple fields
            search_filter = (
                Q(nopa_no__icontains=query) | 
                # Q(invoice_no__icontains=query) |
                Q(pre_nopa__po__po_no__icontains=query) |
                Q(prepared_by__first_name__icontains=query) | 
                Q(prepared_by__last_name__icontains=query) | 
                Q(checked_by__first_name__icontains=query) | 
                Q(checked_by__last_name__icontains=query) | 
                # Q(reviewed_by__first_name__icontains=query) | 
                # Q(reviewed_by__last_name__icontains=query) | 
                # Q(approved_by__first_name__icontains=query) | 
                # Q(approved_by__last_name__icontains=query) | 
                # Q(checked_by_accountant__first_name__icontains=query) | 
                # Q(checked_by_accountant__last_name__icontains=query) | 
                # Q(approved_by_accountant__first_name__icontains=query) | 
                # Q(approved_by_accountant__last_name__icontains=query) | 
                Q(amount_paid_by__first_name__icontains=query) | 
                Q(amount_paid_by__last_name__icontains=query) |
                Q(end_customer_details__icontains=query) | 
                Q(remarks__icontains=query) | 
                Q(utr_no__icontains=query)
            )
            queryset = queryset.filter(search_filter).distinct()

        queryset = queryset.values(
            'id',
            'created_at',
            'nopa_no',
            'pre_nopa__po__po_no',
            'pre_nopa__po__rfq__project_name',
            'pre_nopa__po__supplier__name',
            'amount_paid',
            'amount_percent',
            'prepared_by__first_name',
            'prepared_by__last_name',
            'remarks',
            'pre_nopa__po__rfq__requested_by__first_name',
            'pre_nopa__po__rfq__requested_by__last_name',
            'pre_nopa__po__is_resale',
            'attachments',
            'attachment_list',
            "status",
            "pre_nopa__po__id",
            "pre_nopa__po__rfq__id",
            "payment_date",
            "utr_no",
            "end_customer_details"
        ).order_by('-created_at')
        paginator = Paginator(queryset, 30)
        nopaFinalData = paginator.get_page(page)
        data = []
        for item in nopaFinalData:
            date = getFormattedDate(item["created_at"])
            if item['pre_nopa__po__is_resale']:
                nopaData = {
                    "id": item['id'],
                    "nopa_no": item["nopa_no"],
                    "date": date,
                    "rfq_made_by": "",
                    "po_no": item["pre_nopa__po__po_no"],
                    "project_name": "",
                    "supplier_name": item["pre_nopa__po__supplier__name"],
                    "amount_paid": item["amount_paid"],
                    "amount_percent": item["amount_percent"],
                    "remarks": item["remarks"],
                    "status": get_nopa_status_display(item["status"]),
                    "po_id": item["pre_nopa__po__id"]
                    # "ornate_invoice_no": item["end_customer_details"]["ornate_invoice_number"]
                }
                if item.get("end_customer_details").get("ornate_invoice_number"):
                    nopaData['ornate_invoice_no'] = item["end_customer_details"]["ornate_invoice_number"]
                else:
                    nopaData["ornate_invoice_no"] = ""
            else:    
                nopaData = {
                    "id": item['id'],
                    "nopa_no": item["nopa_no"],
                    "date": date,
                    "rfq_made_by": item["pre_nopa__po__rfq__requested_by__first_name"] + " " + item["pre_nopa__po__rfq__requested_by__last_name"],
                    "po_no": item["pre_nopa__po__po_no"],
                    "project_name": item["pre_nopa__po__rfq__project_name"],
                    "supplier_name": item["pre_nopa__po__supplier__name"],
                    "amount_paid": item["amount_paid"],
                    "amount_percent": item["amount_percent"],
                    "remarks": item["remarks"],
                    "status": get_nopa_status_display(item["status"]),
                    "po_id": item["pre_nopa__po__id"],
                    "rfq_id": item["pre_nopa__po__rfq__id"]
                }
            
            if item["prepared_by__first_name"] is not None:
                nopaData["prepared_by_name"] = item["prepared_by__first_name"] +" "
                if item["prepared_by__last_name"] is not None:
                    nopaData["prepared_by_name"] += item["prepared_by__last_name"]
                else:
                    nopaData["prepared_by_name"] = ""
            else:
                nopaData["prepared_by_name"] = ""

            if item['attachment_list'] is not None:
                nopaData['attachments'] = item['attachments']
                nopaData['attachment_list'] = item['attachment_list']
            else:
                nopaData['attachments'] = item['attachments']
                nopaData['attachment_list'] = []

            if item["utr_no"] is not None:
                nopaData["utr_no"] = item["utr_no"]
                nopaData["payment_date"] = item["payment_date"]
            else:
                nopaData["utr_no"] = ""
                                
            if nopaData["payment_date"] is None:
                nopaData["payment_date"] = ""

            data.append(nopaData)
        if  request.user.role != "Admin":
            data = {
                "nopa" : data,
                "amount_remaining": amount_remaining
            }
        else:
            data = {
                "nopa" : data
            }

        return Response({
            "success": True,
            "status": 200,
            "message": "successful GET request",
            "data": data,
            "total_page_number": nopaFinalData.paginator.num_pages
        }, status=status.HTTP_200_OK)

class NopaApproval(APIView):
    permission_classes = (IsAuthenticated, )
    def get(self, request):
        page = request.query_params.get("page")
        id = request.user.id
        approvals = NOPAApproval.objects.filter(requested_to=id, is_approved=False)
        paginator = Paginator(approvals, 30)
        finalData = paginator.get_page(page)
        data = []

        for item in finalData:
            approval_data = {
                "id": item.id,
                "nopa_id": item.nopa_id.id,
                "supplier_name": item.nopa_id.pre_nopa.po.supplier.name,
                "invoice_no": item.nopa_id.invoice_no,
                "nopa_no": item.nopa_id.nopa_no,
                "made_by": item.nopa_id.prepared_by.first_name + " " + item.nopa_id.prepared_by.last_name,
                "is_approved": item.is_approved 
            }
            data.append(approval_data)
        
        return Response({
                "success": True,
                "message": "successful GET request",
                "status": 200,
                "data": data,
                "total_page_number": finalData.paginator.num_pages
            })
    
    def post(self, request):
        data = request.data
        if data.get("id") is None and data.get("nopa_id"):
            return Response({
                "status": 400,
                "success": False,
                "message": "either id or nopa_id missing"
            })
        approval_id = data["id"]
        nopa_id = data["nopa_id"]
        next_approval = data.get("next_approval_id")
        role = request.user.role
        try:
            nopa = NOPA.objects.get(id = nopa_id)
        except Exception as e:
            return Response({
                "status": 400,
                "success": False,
                "message": "Nopa Does Not Exists"
            })
        user = User.objects.get(id = request.user.id)
        print(request.user.role)

        if role == 'RFQFiller':
            nopa.checked_by = user

        elif role == 'AccountsTeamManager' or role == 'BOSManager':
            nopa.reviewed_by = user

        elif (role == 'SeniorManager' or role == 'Manager') and nopa.reviewed_by is not None:
            nopa.approved_by = user

        elif role == 'FinanceManager':
            nopa.checked_by_accountant = user
        
        elif role == 'FinanceSeniorManager':
            nopa.approved_by_accountant = user
            nopa.status = 2
            
        elif role == "Admin":
            nopa.reviewed_by = user
            nopa.approved_by = user
        else:
            return Response({
                "status": 400,
                "success": False,
                "message": "user is not authorised for approval of nopa"
            })
        
        nopa.save()
        #checking for status
        preNopa = PreNopa.objects.filter(po = nopa.pre_nopa.po)
        is_all_nopa_approved = True
        for item in preNopa:
            nopa_for_status = NOPA.objects.filter(pre_nopa = nopa.pre_nopa)
            # if nopa_for_status.app:
            #     is_all_nopa_approved = False
            for nopa in nopa_for_status:
                if nopa.approved_by is None:
                     is_all_nopa_approved = False
                     
        if is_all_nopa_approved and nopa.pre_nopa.po.amount_remaining == 0:
            # nopa.pre_nopa.po.status = 4
            po = PurchaseOrder.objects.get(id = nopa.pre_nopa.po.id)
            po.status = 4
            po.save()
            if not nopa.pre_nopa.po.is_resale:
                rfq = RFQ.objects.get(nopa.pre_nopa.po.rfq.id)
                rfq.status = 6
                rfq.save()
                # nopa.pre_nopa.po.rfq.status = 6

            nopa.pre_nopa.save()
        #Saving Approval Data
        approval = NOPAApproval.objects.get(id = approval_id)
        approval.is_active = False
        approval.is_approved = True
        approval.save()

        if next_approval is not None:
            user = User.objects.get(id = next_approval)
            approval_data = {
                    "requested_to": user.id,
                    "nopa_id": nopa.id
                }
            serializer = NOPAApprovalSerializer(data=approval_data)
            if serializer.is_valid():
                serializer.save()
                email_from = settings.EMAIL_HOST_USER
                email_to = user.email
                subject = "Reminder Mail"
                message = f"An NOPA with the number {nopa.nopa_no} has been created and is awaiting your approval. Please review it at your earliest convenience."
                recipient_list = [email_to,]
                threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()

        return Response({
            "status": 200,
            "success": True,
            "message": "Nopa approved"
        })
    
class NopaView(APIView):
    permission_classes = (IsAuthenticated, )
    def get(self, request):
        id =  request.query_params.get("id")
        if id == None:
            return Response({
                "success": False,
                "message": "id not provided"
            })
        try:
                nopa = NOPA.objects.get(id=id)
        except Exception as e:
            print(e)
            return Response({
                "status": 400,
                "success": False,
                "error": e
            }, status=status.HTTP_200_OK)
        total_quantity = 0
        for item in nopa.pre_nopa.item_list:
            total_quantity += float(item["quantity"])
        date = getFormattedDate(nopa.created_at)
        if nopa.pre_nopa.po.is_resale:
            nopaData = {
                "nopa_no": nopa.nopa_no,
                "date": date,
                "rfq_no": "",
                "rfq_date":"",
                "rfq_id": "",
                "po_id": nopa.pre_nopa.po.id,
                "rfq_department": "",
                "po_no": nopa.pre_nopa.po.po_no,
                "po_date": getFormattedDate(nopa.pre_nopa.po.created_at),
                "po_made_by": nopa.pre_nopa.po.made_by.first_name + " " + nopa.pre_nopa.po.made_by.last_name,
                "pi_no":nopa.invoice_no,
                "subtotal": nopa.pre_nopa.sub_total,
                "tax_amount": nopa.pre_nopa.tax_amount,
                "total_amount": nopa.pre_nopa.total_amount,
                "payment_terms": nopa.pre_nopa.po.payment_terms,
                "item_list" :  nopa.pre_nopa.item_list,
                "total_quantity": total_quantity,
                "supplier_name": nopa.pre_nopa.po.supplier.name,
                "supplier_gst": nopa.pre_nopa.po.supplier.gst,
                "payment_history": nopa.payment_history,
                "amount_percent_to_be_paid": nopa.amount_percent,
                "total_amount_to_be_paid": nopa.amount_paid,
                "amount_to_be_paid_on_date": nopa.amount_to_be_paid_on_date,
                "amount_outstanding": nopa.pre_nopa.amount_remaining,
                "is_resale": nopa.pre_nopa.po.is_resale,
                "attachments": nopa.attachments,
                }
            nopaData["resale_details"] = nopa.end_customer_details
            nopaData["customer_dilivery_address"] = nopa.pre_nopa.po.customer_delivery_address
        else:
            nopaData = {
                    "nopa_no": nopa.nopa_no,
                    "date": date,
                    "project": nopa.pre_nopa.po.rfq.project_name,
                    "rfq_no": nopa.pre_nopa.po.rfq.rfq_no,
                    "rfq_id": nopa.pre_nopa.po.rfq.id,
                    "po_id": nopa.pre_nopa.po.id,
                    "rfq_date": getFormattedDate(nopa.pre_nopa.po.rfq.created_at),
                    "rfq_department": nopa.pre_nopa.po.rfq.requested_by.department,
                    "po_no": nopa.pre_nopa.po.po_no,
                    "po_date": getFormattedDate(nopa.pre_nopa.po.created_at),
                    "po_made_by": nopa.pre_nopa.po.made_by.first_name + " " + nopa.pre_nopa.po.made_by.last_name,
                    "pi_no":nopa.invoice_no,
                    "subtotal": nopa.pre_nopa.sub_total,
                    "tax_amount": nopa.pre_nopa.tax_amount,
                    "total_amount": nopa.pre_nopa.total_amount,
                    "payment_terms": nopa.pre_nopa.po.payment_terms,
                    "item_list" :  nopa.pre_nopa.item_list,
                    "total_quantity": total_quantity,
                    "supplier_name": nopa.pre_nopa.po.supplier.name,
                    "supplier_gst": nopa.pre_nopa.po.supplier.gst,
                    "payment_history": nopa.payment_history,
                    "amount_percent_to_be_paid": nopa.amount_percent,
                    "total_amount_to_be_paid": nopa.amount_paid,
                    "amount_to_be_paid_on_date": nopa.amount_to_be_paid_on_date,
                    "amount_outstanding": nopa.pre_nopa.amount_remaining,
                    "is_resale": nopa.pre_nopa.po.is_resale,
                    "attachments": nopa.attachments,
                    }
            
            if nopa.pre_nopa.po.rfq.approved_by is not None:
                nopaData["rfq_approved_by"] = nopa.pre_nopa.po.rfq.approved_by.first_name + " " + nopa.pre_nopa.po.rfq.approved_by.last_name 
        
            if nopa.pre_nopa.po.rfq.approved_by_manager is not None:
                nopaData["rfq_approved_by_manager"] = nopa.pre_nopa.po.rfq.approved_by_manager.first_name + " " + nopa.pre_nopa.po.rfq.approved_by_manager.last_name 

        if nopa.attachment_list is not None:
            nopaData["attachment_list"] = nopa.attachment_list

        if nopa.pre_nopa.po.approved_by is not None:
            nopaData["po_approved_by"] = nopa.pre_nopa.po.approved_by.first_name + " " + nopa.pre_nopa.po.approved_by.last_name 

        if nopa.remarks is not None:
            nopaData["remarks"] = nopa.remarks

        if nopa.prepared_by:
            nopaData["requisition_prepared_by"] = nopa.prepared_by.first_name + " " + nopa.prepared_by.last_name

        if nopa.checked_by:
            nopaData["requisition_checked_by"] = nopa.checked_by.first_name + " " + nopa.checked_by.last_name

        if nopa.reviewed_by:
            nopaData["requisition_reviewed_by"] = nopa.reviewed_by.first_name + " " + nopa.reviewed_by.last_name

        if nopa.approved_by:
            nopaData["requisition_approved_by"] = nopa.approved_by.first_name + " " + nopa.approved_by.last_name

        if nopa.checked_by_accountant:
            nopaData["accounts_checked_by"] = nopa.checked_by_accountant.first_name + " " + nopa.checked_by_accountant.last_name

        if nopa.approved_by_accountant:
            nopaData["accounts_approved_by"] = nopa.approved_by_accountant.first_name + " " + nopa.approved_by_accountant.last_name
        if nopa.amount_paid_by is not None and nopa.amount_paid_from is not None:
            nopaData["amount_paid_by"] = nopa.amount_paid_by.first_name + " " + nopa.amount_paid_by.last_name
            nopaData["amount_paid_from"] = nopa.amount_paid_from
        else:
            nopaData["amount_paid_by"] = ""
            nopaData["amount_paid_from"] = ""
        
        return Response({
            "status": 200,
            "success": True,
            "message": "successful GET Request",
            "data": nopaData
        })
    
    def put(self, request):
        data = request.data

        try:
            nopa = NOPA.objects.get(id = data["id"])
        except Exception as e:
            return Response({
                "status": 400,
                "success": False,
                "message": "NOPA Not Found",
                "error": str(e)
            })
        if data.get("utr_no"):
            payment_date = datetime.now().strftime("%Y-%m-%d")
            data["payment_date"] = payment_date
            data["status"] = 3
            
        if data.get("attachment_list"):
            if nopa.attachment_list is None:
                nopa.attachment_list = []
            data["attachment_list"] += nopa.attachment_list
            data["attachments"] = True
        serializer = NOPASerializer(nopa, data = data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status":200,
                "success": True,
                "message": "data saved successfully"
            })
        return Response({
                "status":400,
                "success": False,
                "message": "Problem Saving Data",
                "error": serializer.errors
            })

class FetchNOPAPdf(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        id = request.query_params.get('id')
        if id == None:
            return Response({
                "success": False,
                "message": "id not provided"
            })
        try:
                nopa = NOPA.objects.get(id=id)
        except Exception as e:
            print(e)
            return Response({
                "status": 400,
                "success": False,
                "error": e
            }, status=status.HTTP_200_OK)
        
        return generate_nopa_pdf(nopa.id)

class FetchAllPreNopa(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        page = request.query_params.get("page")
        supplier = request.query_params.get("supplier")
        status2 = request.query_params.get("status")
        query = request.query_params.get("query")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        queryset = PreNopa.objects.all().values(
            'id',
            'created_at',
            'pre_nopa_no',
            'po__po_no',
            'po__rfq__project_name',
            'po__supplier__name',
            'prepared_by__first_name',
            'prepared_by__last_name',
            'po__is_resale',
            'po__supplier',
            'status'
        ).order_by('-created_at')

        if from_date and to_date is not None:
            queryset = queryset.filter(created_at__date__range=[from_date, to_date])
        elif from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        elif to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)

        if supplier:
            #n try:
            #     supplier = Supplier.objects.get(id = int(supplier))
                    queryset = queryset.filter(po__supplier = supplier)
            # except Exception as e:
            #     prit(e)
        
        if status2:
            queryset = queryset.filter(status__icontains = status2)

        if query:
        # Build your Q object for searching across multiple fields
            search_filter = (
                Q(pre_nopa_no__icontains=query) |
                Q(po__po_no__icontains=query) |
                Q(prepared_by__first_name__icontains=query) | 
                Q(prepared_by__last_name__icontains=query)
            )

            queryset = queryset.filter(search_filter).distinct()
        
        queryset.order_by('-created_at')
        

        paginator = Paginator(queryset, 30)
        nopaFinalData = paginator.get_page(page)
        data = []
        print(nopaFinalData)
        for item in nopaFinalData:
            date = getFormattedDate(item["created_at"])
            if item['po__is_resale']:
                nopaData = {
                    "id": item['id'],
                    "nopa_no": item["pre_nopa_no"],
                    "date": date,
                    "po_no": item["po__po_no"],
                    "project_name": "",
                    "supplier_name": item["po__supplier__name"],
                    "status": get_pre_nopa_status_display(item["status"])
                }
            else:    
                nopaData = {
                    "id": item['id'],
                    "nopa_no": item["pre_nopa_no"],
                    "date": date,
                    "po_no": item["po__po_no"],
                    "project_name": item["po__rfq__project_name"],
                    "supplier_name": item["po__supplier__name"],
                    "status": get_pre_nopa_status_display(item["status"])
                }
            
            if item["prepared_by__first_name"] is not None:
                nopaData["prepared_by_name"] = item["prepared_by__first_name"] + " "
                if item["prepared_by__last_name"] is not None:
                    nopaData["prepared_by_name"] += item["prepared_by__last_name"]
            data.append(nopaData)
            
        return Response({
            "success": True,
            "status": 200,
            "message": "successful GET request",
            "data": data,
            "total_page_number": nopaFinalData.paginator.num_pages
        }, status=status.HTTP_200_OK)

class PreNopaView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        id = request.query_params.get("pre_nopa_id")
        if id is None:
            return({
                "status": 400,
                "success": False,
                "message": "id not provided"
            })

        try:
            pre_nopa = PreNopa.objects.get(id = id)
        except Exception as e:
             return({
                "status": 400,
                "success": False,
                "message": "Pre Nopa Not Found"
            })

        if pre_nopa.po.is_resale:
            data = {
                "pre_nopa_id": pre_nopa.id,
                "pre_nopa_no" : pre_nopa.pre_nopa_no,
                "requested_by_name": "",
                "requested_by_department" : "",
                "requested_to_name": "",
                "priority": "",
                "rfq_no": "",
                "rfq_date": "",
                "rfq_department": "",
                "pre_nopa_date": getFormattedDate(pre_nopa.created_at),
                "po_no": pre_nopa.po.po_no,
                "supplier": pre_nopa.po.supplier.name,
                "made_by":pre_nopa.po.made_by.first_name + " " + pre_nopa.po.made_by.last_name,
                "remarks": (pre_nopa.po.remarks or ""),
                "total_amount": pre_nopa.total_amount,
                "sub_total" : pre_nopa.sub_total,
                "item_list": pre_nopa.item_list,
                "amount_remaining": pre_nopa.amount_remaining,
                "tax_amount": pre_nopa.tax_amount,
                "supplier_gst": pre_nopa.po.supplier.gst,
                "is_resale" : pre_nopa.po.is_resale,
                "is_project": pre_nopa.po.is_project,
                "po_date": getFormattedDate(pre_nopa.po.created_at)
            }
            if pre_nopa.po.project is not None:
                data["company_name"] = pre_nopa.po.project.name
                data["company_address"] = pre_nopa.po.project.address + " " + pre_nopa.po.project.city + " " + pre_nopa.po.project.state + " " + pre_nopa.po.project.pincode
                data["company_city"] = pre_nopa.po.project.city
                data["company_gst"] = pre_nopa.po.project.gst
                data["project"] = pre_nopa.po.project.name
            else:
                data["company_name"] =""
                data["company_address"] = ""
                data["company_city"] = ""
                data["company_gst"] = ""
                data["project"] = pre_nopa.po.contract_no
        else:
            data = {
                    "pre_nopa_id": pre_nopa.id,
                    "pre_nopa_no" : pre_nopa.pre_nopa_no,
                    "requested_by_name": pre_nopa.po.rfq.requested_by.first_name + " " + pre_nopa.po.rfq.requested_by.last_name,
                    "requested_by_department" : pre_nopa.po.rfq.requested_by.department,
                    "requested_to_name": pre_nopa.po.rfq.requested_to.first_name + " " + pre_nopa.po.rfq.requested_to.last_name,
                    "priority": pre_nopa.po.rfq.priority,
                    "rfq_no": pre_nopa.po.rfq.rfq_no,
                    "rfq_date": getFormattedDate(pre_nopa.po.rfq.created_at),
                    "rfq_department": pre_nopa.po.rfq.requested_by.department,
                    "po_date": getFormattedDate(pre_nopa.po.created_at),
                    "po_no": pre_nopa.po.po_no,
                    "supplier": pre_nopa.po.supplier.name,
                    "project": (pre_nopa.po.rfq.project_name or ""),
                    "made_by":pre_nopa.po.made_by.first_name + " " + pre_nopa.po.made_by.last_name,
                    "remarks": (pre_nopa.po.remarks or ""),
                    "total_amount": pre_nopa.total_amount,
                    "sub_total" : pre_nopa.sub_total,
                    "item_list": pre_nopa.item_list,
                    "amount_remaining": pre_nopa.amount_remaining,
                    "tax_amount": pre_nopa.tax_amount,
                    "supplier_gst": pre_nopa.po.supplier.gst,
                    "is_resale" : pre_nopa.po.is_resale,
                    "po_date": getFormattedDate(pre_nopa.po.created_at)
            }
            data["company_name"] =""
            data["company_address"] = ""
            data["company_city"] = ""
            data["company_gst"] = ""

            if pre_nopa.po.rfq.approved_by is not None and pre_nopa.po.rfq.approved_by.first_name is not None:
                data["rfq_approved_by"] = (pre_nopa.po.rfq.approved_by.first_name or "") + " " + (pre_nopa.po.rfq.approved_by.last_name or "")
            else:
                data["rfq_approved_by"] = ""

            if pre_nopa.po.rfq.approved_by_manager is not None and pre_nopa.po.rfq.approved_by_manager.first_name is not None:
                data["rfq_approved_by_manager"] = (pre_nopa.po.rfq.approved_by_manager.first_name or "") + " " + (pre_nopa.po.rfq.approved_by_manager.last_name or "")
            else:
                data["rfq_approved_by_manager"] = ""
        
        if pre_nopa.po.approved_by is not None and pre_nopa.po.approved_by.first_name is not None:
            data["approved_by"] = (pre_nopa.po.approved_by.first_name or "") + " " + (pre_nopa.po.approved_by.last_name or "")
        else:
            data["approved_by"] = ""

        return Response({
            "status": 200,
            "success": True,
            "message": "successfull GET Request",
            "data": data
        })

class ExcelExportView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        id = request.user.id
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
            
        query_set = NOPA.objects.filter(prepared_by = id)
        if from_date and to_date is not None:
            query_set = query_set.filter(created_at__date__range=[from_date, to_date])

        query_set = query_set.order_by('created_at')
        
        query_set = query_set.values(
            'created_at',
            'nopa_no',
            'invoice_no',
            'pre_nopa__po__rfq__description',
            'pre_nopa__item_list',
            'amount_paid',
            'pre_nopa__po__supplier__name',
            'pre_nopa__po__rfq__project_name',
            'pre_nopa__po__rfq__material_category',
            'pre_nopa__po__rfq__requested_by__first_name',
            'pre_nopa__po__rfq__requested_by__last_name',
            'status',
            'remarks',
            'pre_nopa__amount_remaining',
            'pre_nopa__po__is_resale',
            'end_customer_details',
            "pre_nopa__po__made_by__first_name",
            "pre_nopa__po__made_by__last_name",
            "pre_nopa__payment_history",
            "mode_of_payment"
        )
        wb = Workbook()
        ws = wb.active
        headers = [ 
                    "Nopa Date", 
                    "Nopa No", 
                    "Invoice No", 
                    "Project Description", 
                    "Quantity",
                    "Nopa Amount",
                    "Vendor",
                    "Customer",
                    "Ornate Invoice Number",
                    "Payment Status",
                    "Profit",
                    "Category",
                    "Request Raised By",
                    "Advanced Paid",
                    "Advance Paid Date",
                    "Payment Mode",
                    "Remarks",
                    "Balance Payable",
                  ]
        ws.append(headers)
        fd = []
        for item in query_set:
            date = getFormattedDate(item["created_at"])
            quantity = 0.0
            for item2 in item["pre_nopa__item_list"]:
                quantity += float(item2["quantity"])
            
            advanced_paid = 0.0
            advanced_paid_date = ""
            for history in item["pre_nopa__payment_history"]:
                advanced_paid  += history["amount_paid"]
                advanced_paid_date  = history["date"]
            
            status = "Unpaid"
            if item["status"] == "Paid":
                status = "Paid"
            
            if item['pre_nopa__po__is_resale']:
                customer_name = item["end_customer_details"]["company_name"]
                ornate_invoice_no = item["end_customer_details"]["ornate_invoice_number"]
                profit = item["end_customer_details"]["profit"]
                data = [
                    date,
                    item["nopa_no"],
                    item["invoice_no"],
                    "N/A",
                    str(quantity),
                    item["amount_paid"],
                    item["pre_nopa__po__supplier__name"],
                    customer_name,
                    ornate_invoice_no,
                    status,
                    profit,
                    "N/A",
                    item["pre_nopa__po__made_by__first_name"] + " " + item["pre_nopa__po__made_by__last_name"],
                    advanced_paid,
                    advanced_paid_date,
                    item["mode_of_payment"],
                    item["remarks"],
                    item["pre_nopa__amount_remaining"]
                ]
            else:
                data = [
                    date,
                    item["nopa_no"],
                    item["invoice_no"],
                    item["pre_nopa__po__rfq__description"],
                    str(quantity),
                    item["amount_paid"],
                    item["pre_nopa__po__supplier__name"],
                    "N/A",
                    "N/A",
                    status,
                    "N/A",
                    item["pre_nopa__po__rfq__material_category"],
                    item["pre_nopa__po__rfq__requested_by__first_name"] + " " + item["pre_nopa__po__rfq__requested_by__last_name"],
                    advanced_paid,
                    advanced_paid_date,
                    item["mode_of_payment"],
                    item["remarks"],
                    item["pre_nopa__amount_remaining"]
                ]
            ws.append(data)
        
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        response = HttpResponse(excel_buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=exported_data.xlsx"
        return response