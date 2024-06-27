import re
import threading
from django.shortcuts import render
from datetime import datetime
from django.shortcuts import render
from django.core.paginator import Paginator
from django.core.mail import send_mail
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from weasyprint import HTML
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from num2words import num2words
from openpyxl.styles import Alignment


from accounts.models import User
from nopa.models import Supplier
from nopa_backend import settings
from rfq.utils import getFormattedDate

from .models import POApproval, Projects, PurchaseOrder

from .utils import generate_po_no, get_status_display
from rfq.models import RFQ
from rfq.serializer import RFQItemListUpdateSerializer
from django.core.paginator import Paginator
from openpyxl import Workbook
from io import BytesIO

from .serializer import POApprovalSerializer, ProjectsSerializer, PurchaseOrderSerializer, RFQSerializer
# Create your views here.

def generate_po_pdf(id):

    try: 
        po = PurchaseOrder.objects.get(id=id)
    except Exception as e:
         return Response({
                'success': False,
                'status': 404,
                'message': 'Purchase Order not found'
                }, status=status.HTTP_200_OK)

    formattedDate = getFormattedDate(po.created_at)
    if po.delivery_terms:
            delivery_terms = po.delivery_terms
            delivery_terms  = re.split(r"\s*'\d+\.'\s*", delivery_terms)
    if po.item_list:
        for item in po.item_list:
            if item.get("item_description") is not None:
                description = item["item_description"]
                description = re.split(r"\s*'\d+\.'\s*", description)
                item["item_description"] = description
            else:
                item["item_description"] = ""
    is_t_and_c = False
   

    context = {
                "purchase_order_no": po.po_no,
                "date": formattedDate,
                "purchaser_name": po.purchaser.name,
                "purchaser_address": po.purchaser.address + " " + po.purchaser.city + " " + po.purchaser.state + " " + po.purchaser.pincode,
                "purchaser_gst": po.purchaser.gst,
                "supplier_name": po.supplier.name,
                "supplier_address": po.supplier.address + " " + po.supplier.city + " " + po.supplier.state + " " + po.supplier.pincode,
                "supplier_gst": po.supplier.gst,
                "item_list" : po.item_list,
                "subtotal": po.sub_total,
                "tax_amount": po.tax_amount,
                "total_amount": po.total_amount,
                "total_amount_words": num2words(po.total_amount, to='currency', lang='en_IN', currency="INR"),
                "payment_terms": po.payment_terms,
                "delivery_terms": delivery_terms,
                "made_by": po.made_by.first_name.title() + " " + po.made_by.last_name.title(),
                "made_by_email" : po.made_by.email,
                "made_by_phone": po.made_by.contact_number,
                "purchaser": po.purchaser.id,
                "is_project": po.is_project,
                "revision": po.revision,
                "is_approved": po.is_approved
                }
    if po.terms_and_conditions is not None:
            t_and_c = po.terms_and_conditions
            t_and_c  = re.split(r'\s*\d+\.\s*', t_and_c)
            t_and_c = [item for item in t_and_c if item]  
            is_t_and_c = True
            if len(t_and_c) == 0:
                is_t_and_c = False
            context["teams_and_conditions"] = t_and_c

    context["is_t_and_c"] = is_t_and_c
    
    if po.revision_remark is not None:
        context['revision_remark'] = po.revision_remark
    if po.contract_no is not None:
        context["contract_no"] = po.contract_no
    if po.is_resale:
        context["customer_delivery_address"] = po.customer_delivery_address
        context["contact_person_name"] = po.contact_person_name
        context["contact_person_phone"] = po.contact_person_phone
        if po.is_project:
            context["project_name"] = po.project.name
            context["project_gst"] = po.project.gst

    if po.is_approved:
        context["approved_by"] = po.approved_by.first_name.title() + " " + po.approved_by.last_name.title()

    html_string1 = get_template('po.html').render(context)
    pdf_file = HTML(string=html_string1).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="po.pdf"'
    return response

class GeneratePO(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request, format=None):
        updated_item_list = request.data.get('item_list')
        data = request.data
    
        if not data["is_resale"]:
            rfq_id = request.data.get('rfq')
            try:
                rfq = RFQ.objects.get(id=rfq_id)
                #checking for approval done or not
                if rfq.approved_by is None:
                    return Response({
                            'success': False,
                            'status': 404,
                            'message': 'RFQ not approved'
                            }, status=status.HTTP_200_OK)
                
                #Checking if senior approval needed 
                if rfq.is_manager_approval:
                    if rfq.approved_by_manager is None:
                        return Response({
                            'success': False,
                            'status': 404,
                            'message': 'RFQ not approved'
                            }, status=status.HTTP_200_OK)
                    
            except RFQ.DoesNotExist:
                return Response({
                    'success': False,
                    'status': 404,
                    'message': 'RFQ not found'
                    }, status=status.HTTP_200_OK)
            
            # rfqSerializer = RFQItemListUpdateSerializer(rfq, data={'item_list': item_list_data}, partial=True)
            # if rfqSerializer.is_valid():
            #     rfqSerializer.save()
            # else:
            #     return Response({
            #         'success': False,
            #         'status': 404,
            #         'message': 'unsuccessful',
            #         'error': rfqSerializer.errors
            #     }, status=status.HTTP_200_OK)
            # Updating item_list
            item_list = rfq.item_list
            is_rfq_completed = True
            for updated_item in updated_item_list:
                updated_item["is_nopa_generated"] = False
                for item in item_list:
                    if updated_item['id'] == item['id']:
                        item['is_po_generated'] = True
                    
            data['purchaser'] = rfq.purchaser.id
            for item in item_list:
                if not item['is_po_generated']:
                        is_rfq_completed = False       

            rfqSerializer = RFQItemListUpdateSerializer(rfq, data={'item_list': item_list, 'is_po_generated' : True, 'is_rfq_closed': is_rfq_completed}, partial=True)
            if not rfqSerializer.is_valid():
                return Response({
                    'success': False,
                    'status': 404,
                    'message': 'unsuccessful',
                    'error': rfqSerializer.errors
                }, status=status.HTTP_200_OK)
        else: 
            for i, item in enumerate(updated_item_list):
                    item['id'] = i + 1
                    item['is_nopa_generated'] = False
        subtotal=0
        tax_amount = 0
        total_amount=0
        for item in updated_item_list:
            subtotal += item["sub_total"]
            tax_amount += item['tax_amount']
        tax_amount = round(tax_amount, 2)
        subtotal = round(subtotal, 2)
        total_amount = subtotal + tax_amount
        total_amount = round(total_amount)
        print(total_amount)
        # po_no = generate_po_no()
        # data['po_no'] = po_no
        data['tax_amount'] = tax_amount
        data['sub_total'] = subtotal
        data['total_amount'] = total_amount
        data['amount_remaining'] = subtotal
        if data.get('made_by') is None:
            data['made_by'] = request.user.id
        data['payment_history'] = []
        serializer = PurchaseOrderSerializer(data=data)
        if serializer.is_valid():
           
            data = serializer.save()
            po = PurchaseOrder.objects.get(id=data.id)
            po.po_no = generate_po_no(po.id, po.purchaser.id)

            #sending for approval
            if request.data.get('is_approval_needed'): 
                approval_data = {
                    "requested_to": request.data.get('approval_manager_id'),
                    "po_id": data.id
                }
                approval_serializer  = POApprovalSerializer(data=approval_data)

                if approval_serializer.is_valid():
                    approval_serializer.save()
                    email_from = settings.EMAIL_HOST_USER
                    email_to = User.objects.get(id = request.data.get('approval_manager_id')).email
                    subject = "Reminder Mail"
                    message = f"An PO with the number {po.po_no} has been created and is awaiting your approval. Please review it at your earliest convenience."
                    recipient_list = [email_to,]
                    threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()
                else:
                    return Response({
                        'success': False,
                        'status': 404,
                        'message': 'approval data not correct',
                        'error': approval_serializer.errors
                    }, status=status.HTTP_200_OK)
            else:
                date = datetime.now().strftime('%Y-%m-%d')
                user = User.objects.get(id = request.user.id)
                po.approved_by = user
                po.approved_by_date = date
                po.is_approved = True
                po.status = 2
            po.save()
            if not po.is_resale:
                if rfqSerializer.is_valid():
                    rfqSerializer.save()
            if not po.is_resale:
                rfq = RFQ.objects.get(id = po.rfq.id)
                is_all_item_po_generated = True
                for item in  rfq.item_list:
                    print(item["is_po_generated"])
                    if not item["is_po_generated"]:
                        is_all_item_po_generated = False
                if is_all_item_po_generated:
                    rfq.is_rfq_closed = True

                rfq.status = 3
                status_po = PurchaseOrder.objects.filter(rfq = rfq.id)
                is_all_po_approved = True

                for item in status_po:
                    if not item.is_approved:
                        is_all_po_approved = False

                if is_all_po_approved:
                    rfq.status = 4
                rfq.save()
            return generate_po_pdf(po.id)
        print(serializer.errors)
        return Response({
                'success': False,
                'status': 404,
                'message': 'unsuccessful',
                'error': serializer.errors
            }, status=status.HTTP_200_OK)

class FetchAllPO(APIView):
    permission_classes= (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        page = request.query_params.get("page")
        id = request.user.id
        status2 = request.query_params.get("status")
        is_export = request.query_params.get("is_export")
        query = request.query_params.get("query")
        supplier = request.query_params.get("supplier")
        purchaser = request.query_params.get("purchaser")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        # is_project = request.query_params.get("is_project")
        # is_resale = request.query_params.get("is_resale")
        po_type = request.query_params.get("po_type")

        project = request.query_params.get("project")
        queryset = PurchaseOrder.objects.filter(made_by=id)
        print(request.user.role)
        if request.user.role == 'Finance' or  request.user.role == 'FinanceManager' or  request.user.role == 'FinanceSeniorManager':
            queryset = PurchaseOrder.objects.all()

        if request.user.role == 'Admin' or  request.user.role == 'AccountsTeamManager':
            queryset = PurchaseOrder.objects.all()

        # if request.user.role == 'BOSFiller':
        #     queryset = PurchaseOrder.objects.filter(is_resale = True)

        if request.user.role == 'BOSManager' or request.user.role == 'BOSFiller':
            queryset = PurchaseOrder.objects.filter(is_resale = True)

        if query:
        # Build your Q object for searching across multiple fields
            search_filter = Q(po_no__icontains=query) | Q(purchaser__name__icontains=query) | Q(project__name__icontains=query) | Q(supplier__name__icontains=query) | Q(rfq__rfq_no__icontains=query)
            queryset = queryset.filter(search_filter).distinct()
        if status2:
            queryset = queryset.filter(status__iexact=status2)

        if supplier:
            queryset = queryset.filter(supplier = supplier)

        if purchaser:
            queryset = queryset.filter(purchaser = purchaser)

        if project:
            queryset = queryset.filter(project = project)

        # if from_date and to_date is not None:
        #     queryset = queryset.filter(created_at__date__range=[from_date, to_date])

        # if is_project:
        #     queryset = queryset.filter(is_project = is_project)

        # if is_resale:
        #     queryset = queryset.filter(is_resale = is_resale, is_project = False)

        if po_type:
            if po_type == 'resale':
                queryset = queryset.filter(is_resale = True, is_project = False)
            if po_type == 'project':
                queryset = queryset.filter(is_project = True)
            if po_type == 'normal':
                queryset = queryset.filter(is_resale = False, is_project = False)
                
        if from_date and to_date is not None:
            queryset = queryset.filter(created_at__date__range=[from_date, to_date])
        elif from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        elif to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        queryset = queryset.values(
            "id", 
            "rfq__rfq_no", 
            "rfq__requested_by__first_name", 
            "rfq__requested_by__last_name", 
            "rfq__requested_by__department",
            "rfq__requested_to__first_name", 
            "rfq__requested_to__last_name", 
            "rfq__priority",
            "rfq__rfq_no",
            "po_no",
            "created_at",
            "supplier__name",
            "rfq__project_name",
            "made_by__first_name", 
            "made_by__last_name", 
            "approved_by__first_name", 
            "approved_by__last_name",
            "total_amount" ,
            "remarks",
            "is_po_closed",
            "is_resale",
            "is_approved",
            "contract_no",
            "item_list",
            "status",
            "is_project",
            "project__name"
            ).order_by("-created_at")
        if not is_export:
            paginator = Paginator(queryset, 30)
            poFinalData = paginator.get_page(page)
            data = []
            for item in poFinalData:
                formatted_date = getFormattedDate(item["created_at"])
                if item["is_resale"] == True:
                    poData = {
                        "id": item["id"],
                        "requested_by_name":"",
                        "requested_by_department" : "",
                        "requested_to_name": "",
                        "priority": "",
                        "date": formatted_date,
                        "po_no": item["po_no"],
                        "supplier": item["supplier__name"],
                        "made_by": item["made_by__first_name"] + " " + item["made_by__last_name"],
                        "approved_by": (item["approved_by__first_name"] or "") + " " +(item["approved_by__last_name"] or ""),
                        "remarks": (item["remarks"] or ""),
                        "total_amount": item["total_amount"],
                        "is_po_closed": item["is_po_closed"],
                        "is_approved": item["is_approved"],
                        "is_resale": item["is_resale"],
                        "status": get_status_display(item["status"]),
                    }
                    if item.get("is_project"):
                        poData["project"] = item["project__name"]
                        poData["rfq_no"] = item["project__name"]
                    else:
                        if item.get("contract_no"):
                            poData["project"] = item["contract_no"]
                            poData["rfq_no"] = item["contract_no"]
                        else:
                            poData["project"] = ""
                            poData["rfq_no"] =""
                else:    
                    poData = {
                        "id": item["id"],
                        "requested_by_name": item["rfq__requested_by__first_name"] + " " + item["rfq__requested_by__last_name"],
                        "requested_by_department" : item["rfq__requested_by__department"],
                        "requested_to_name": item["rfq__requested_to__first_name"] + " " + item["rfq__requested_to__last_name"],
                        "priority": item["rfq__priority"],
                        "rfq_no": item["rfq__rfq_no"],
                        "date": formatted_date,
                        "po_no": item["po_no"],
                        "supplier": item["supplier__name"],
                        "project": (item["rfq__project_name"] or "" ),
                        "made_by": item["made_by__first_name"] + " " + item["made_by__last_name"],
                        "approved_by": (item["approved_by__first_name"] or "") + " " +(item["approved_by__last_name"] or ""),
                        "remarks": (item["remarks"] or ""),
                        "total_amount": item["total_amount"],
                        "is_po_closed": item["is_po_closed"],
                        "is_approved": item["is_approved"],
                        "is_resale": item["is_resale"],
                        "status":  get_status_display(item["status"]),
                    }
                # if item["contract_no"] is not None:
                #     poData["contract_no"] = item["contract_no"]
                # else:
                #     poData["contract_no"] = ""
                
                data.append(poData)
            return JsonResponse({
                        "status": 200,
                        "success": True,
                        "data": data,
                        "total_page_number": poFinalData.paginator.num_pages
                    }, status=status.HTTP_200_OK)
        else:
            print()
            wb = Workbook()
            ws = wb.active
            headers = [ 
                    "PO Date", 
                    "RFQ No", 
                    "PO No", 
                    "Vendor Name", 
                    "Project",
                    "items",
                    "Total Amount",
                    "Made By",
                    "Status",
                    "Approved By",
                    "Remarks",
                  ]
        ws.append(headers)
        fd = []

        for item in queryset:
            date = getFormattedDate(item["created_at"])
            if item['is_resale']:
                if item.get('contract_no'):
                    project = item["contract_no"]
                if item['is_project']:
                    project = item['project__name']
                rfq_no = ""
            else:
                project = item['rfq__project_name']
                rfq_no = item['rfq__rfq_no']
                
                
            if item.get('approved_by__first_name') is not None:
                approved_by = item["approved_by__first_name"].title() + ' ' + item['approved_by__last_name'].title()
            else:
                approved_by = ""
            #for item list
            item_list = ""
            i = 1
            # print(item["item_list"])
            for items in item["item_list"]:
                if items.get('unit') is None:
                    unit = "pcs."
                else:
                    unit = items.get('unit')
                item_list += (str(i) + ". " + items.get('item', '') + " - " + str(items.get("quantity")) + " " + unit +" @ ₹" + str(items.get('total_amount')) +"   ")
                i+=1
            data = [
                date,
                rfq_no,
                item["po_no"],
                item["supplier__name"],
                project,
                item_list,
                item['total_amount'],
                item['made_by__first_name'] + item['made_by__last_name'],
                get_status_display(item["status"]),
                approved_by,
                (item["remarks"] or ""),
            ]

            ws.append(data)
            for cell in ws['F']:
                cell.alignment = Alignment(wrap_text=True)
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        response = HttpResponse(excel_buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=exported_data.xlsx"
        return response
  
class FetchPOPdf(APIView):
    permission_classes= (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        id = request.query_params.get("id")
        if id is None:
            return Response({
                "success": False,
                "message": "please provide id",
                "status": 400
            })
        return generate_po_pdf(id)

class POView(APIView):
    permission_classes= (IsAuthenticated, )

    def get(self, request):
        id = request.query_params.get("id")
        if id == None:
            return Response({
                "success": False,
                "message": "id not provided"
            })

        try:
                po = PurchaseOrder.objects.get(id=id)
        except Exception as e:
            print(e)
            return Response({
                "status": 400,
                "success": False,
                "error": e
            }, status=status.HTTP_200_OK)
        item_list = po.item_list
        formatted_date = getFormattedDate(po.created_at)
        if po.is_resale == True:
            poData = {
                    "id": po.id,
                    "requested_by_name": "",
                    "requested_by_department" : "",
                    "requested_to_name": "",
                    "priority": "",
                    "rfq_no": "",
                    "rfq_date": "",
                    "rfq_department": "",
                    "po_date": formatted_date,
                    "po_no": po.po_no,
                    "supplier_id": po.supplier.id,
                    "supplier": po.supplier.name,
                    "purchaser": po.purchaser.id,
                    "contact_person_name" : po.contact_person_name,
                    "contact_person_phone" : po.contact_person_phone,
                    "is_project": po.is_project,
                    "payment_terms": po.payment_terms,
                    "delivery_terms": po.delivery_terms,
                    "made_by":po.made_by.first_name + " " + po.made_by.last_name,
                    "remarks": (po.remarks or ""),
                    "total_amount": po.total_amount,
                    "sub_total" : po.sub_total,
                    "item_list": po.item_list,
                    "amount_remaining": po.amount_remaining,
                    "tax_amount": po.tax_amount,
                    "supplier_gst": po.supplier.gst,
                    "is_resale" : po.is_resale,
                    "customer_delivery_address": po.customer_delivery_address
                }
            if po.project is not None:
                poData["company_name"] = po.project.name
                poData["company_address"] = po.project.address + " " + po.project.city + " " + po.project.state + " " + po.project.pincode
                poData["company_city"] = po.project.city
                poData["company_gst"] = po.project.gst
                poData["project"] = po.project.id
            else:
                poData["company_name"] =""
                poData["company_address"] = ""
                poData["company_city"] = ""
                poData["company_gst"] = ""
                poData["project"] = ""
        
        else:   
            poData = {
                    "id": po.id,
                    "rfq_id": po.rfq.id,
                    "requested_by_name": po.rfq.requested_by.first_name + " " + po.rfq.requested_by.last_name,
                    "requested_by_department" : po.rfq.requested_by.department,
                    "requested_to_name": po.rfq.requested_to.first_name + " " + po.rfq.requested_to.last_name,
                    "priority": po.rfq.priority,
                    "rfq_no": po.rfq.rfq_no,
                    "rfq_date": getFormattedDate(po.rfq.created_at),
                    "rfq_department": po.rfq.requested_by.department,
                    "po_date": formatted_date,
                    "is_project": po.is_project,
                    "po_no": po.po_no,
                    "purchaser": po.purchaser.id,
                    "supplier_id": po.supplier.id,
                    "supplier": po.supplier.name,
                    "payment_terms": po.payment_terms,
                    "delivery_terms": po.delivery_terms,
                    "project": (po.rfq.project_name or ""),
                    "made_by":po.made_by.first_name + " " + po.made_by.last_name,
                    "remarks": (po.remarks or ""),
                    "total_amount": po.total_amount,
                    "sub_total" : po.sub_total,
                    "item_list": po.item_list,
                    "amount_remaining": po.amount_remaining,
                    "tax_amount": po.tax_amount,
                    "supplier_gst": po.supplier.gst,
                    "is_resale" : po.is_resale
                }
            if po.rfq.approved_by is not None and po.rfq.approved_by.first_name is not None:
                poData["rfq_approved_by"] = (po.rfq.approved_by.first_name or "") + " " + (po.rfq.approved_by.last_name or "")
            else:
                poData["rfq_approved_by"] = ""

            if po.rfq.approved_by_manager is not None and po.rfq.approved_by_manager.first_name is not None:
                poData["rfq_approved_by_manager"] = (po.rfq.approved_by_manager.first_name or "") + " " + (po.rfq.approved_by_manager.last_name or "")
            else:
                poData["rfq_approved_by_manager"] = ""
        if po.approved_by is not None and po.approved_by.first_name is not None:
            poData["approved_by"] = (po.approved_by.first_name or "") + " " + (po.approved_by.last_name or "")
        else:
            poData["approved_by"] = ""
        if po.contract_no is not None:
            poData["contract_no"] = po.contract_no
        else:
            poData["contract_no"] = ""
        return Response({
             "success": True,
             "status": 200,
             "message": "Successful GET request",
             "data": poData
        })
    
    def put(self, request):
        data = request.data

        try:
            purchase_order = PurchaseOrder.objects.get(id=data["id"])
        except PurchaseOrder.DoesNotExist:
            return Response({
                "status": 200,
                "success": True,
                "message": "Po Not Found"
            })
        print(data)
        if data.get('item_list'):
            subtotal=0
            tax_amount = 0
            total_amount=0
            for item in data['item_list']:
                subtotal += item["sub_total"]
                tax_amount += round(item['tax_amount'])
            tax_amount = tax_amount
            total_amount = subtotal + tax_amount
            total_amount = round(total_amount)
            # po_no = generate_po_no()
            # data['po_no'] = po_no
                            
            if data.get("supplier") is not None:
                data["supplier"] = Supplier.objects.get(id = int(data["supplier"])).id
            data['tax_amount'] = tax_amount
            data['sub_total'] = round(subtotal)
            data['total_amount'] = total_amount
            data['amount_remaining'] = round(subtotal)
        data['revision'] = purchase_order.revision + 1
        if purchase_order.approved_by is not None:
            data["approved_by"] = purchase_order.approved_by.id
        serializer = PurchaseOrderSerializer(purchase_order, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "data successfully saved"
            })
        return Response({
            "status": 400,
            "success": False,
            "message": "data not saved",
            "error": serializer.errors
        })

class POApprovalView(APIView):
    permission_classes= (IsAuthenticated, )
    def get(self, request):
        # id = request.query_params.get("id")
        page = request.query_params.get("page")
        id = request.user.id
        approvals = POApproval.objects.filter(requested_to=id, is_approved=False)
        paginator = Paginator(approvals, 30)
        finalData = paginator.get_page(page)
        data = []
        for item in finalData:
            approval_data = {
                "id": item.id,
                "po_id": item.po_id.id,
                "po_no": item.po_id.po_no,
                "made_by": item.po_id.made_by.first_name + " " + item.po_id.made_by.last_name,
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
            po_id = data["po_id"]
            approval_id = data["id"]
            approvals = POApproval.objects.get(id = approval_id)
            if approvals.is_approved:
                return Response({
                    "success": False,
                    "message": "PO Already Approved",
                    "status": 400,
                })
            po = PurchaseOrder.objects.get(id = po_id)
            date = datetime.now().strftime('%Y-%m-%d')
            if request.user.role == 'AccountsTeamManager' or request.user.role == 'BOSManager':
                user = User.objects.get(id=request.user.id)
                po.approved_by = user
                po.approved_by_date = date
                po.is_approved = True
                po.status = 2
            else:
                return Response({
                    "success": False,
                    "message": "only manager can approve RFQ",
                    "status": 400,
                })
            po.save()

            if not po.is_resale:
                po_for_status = PurchaseOrder.objects.filter(rfq = po.rfq)
                is_all_po_approved = True
                for item in po_for_status:
                    if not item.is_approved and not item.amount_remaining == 0:
                        is_all_po_approved = False

                if is_all_po_approved:
                    rfq = RFQ.objects.get(id = po.rfq.id)
                    rfq.status = 4
                    rfq.save()

            approvals.is_approved = True
            approvals.is_active = False
            approvals.save()

            email_from = settings.EMAIL_HOST_USER
            email_to = list(User.objects.filter(role__in =['Finance']).values_list('email', flat=True))
            subject = "Reminder Mail"
            message = f"An PO with the number {po.po_no} has been Approved and is awaiting to create NOPA. Please review it at your earliest convenience."
            recipient_list = email_to
            threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()

            return Response({
                "success": True,
                "message": "PO Approved",
                "status": 200,
            })

class FetchPOGeneratedRFQ(APIView):
    permission_classes = (IsAuthenticated, )
    def get(self, request):
        page = request.query_params.get("page")
        queryset = PurchaseOrder.objects.filter(
            Q(rfq__is_po_generated=True) | Q(is_resale=True),
            made_by=request.user.id
            ).distinct('rfq')
        
        queryset = queryset.values(
            "id", 
            "rfq", 
            "rfq__requested_by__first_name", 
            "rfq__requested_by__last_name", 
            "rfq__requested_by__department",
            "rfq__requested_to__first_name", 
            "rfq__requested_to__last_name", 
            "rfq__priority",
            "rfq__rfq_no",
            "po_no",
            "created_at",
            "supplier__name",
            "rfq__project_name",
            "made_by__first_name", 
            "made_by__last_name", 
            "approved_by__first_name", 
            "approved_by__last_name",
            "total_amount" ,
            "remarks",
            "is_po_closed",
            "is_resale",
            "is_approved"
            )
        paginator = Paginator(queryset, 30)
        poFinalData = paginator.get_page(page)
        data = []
        for item in poFinalData:
            formatted_date = getFormattedDate(item["created_at"])
            if item["is_resale"] == True:
                poData = {
                    "id": item["id"],
                    "requested_by_name":"",
                    "requested_by_department" : "",
                    "requested_to_name": "",
                    "priority": "",
                    "rfq_no": "",
                    "date": formatted_date,
                    "po_no": item["po_no"],
                    "supplier": item["supplier__name"],
                    "project": "",
                    "made_by": item["made_by__first_name"] + " " + item["made_by__last_name"],
                    "approved_by": (item["approved_by__first_name"] or "") + " " +(item["approved_by__last_name"] or ""),
                    "remarks": (item["remarks"] or ""),
                    "total_amount": item["total_amount"],
                    "is_po_closed": item["is_po_closed"],
                    "is_approved": item["is_approved"],
                    "rfq_id": "",
                    "is_resale": item["is_resale"]
                }
            else:    
                poData = {
                    "id": item["id"],
                    "requested_by_name": item["rfq__requested_by__first_name"] + " " + item["rfq__requested_by__last_name"],
                    "requested_by_department" : item["rfq__requested_by__department"],
                    "requested_to_name": item["rfq__requested_to__first_name"] + " " + item["rfq__requested_to__last_name"],
                    "priority": item["rfq__priority"],
                    "rfq_no": item["rfq__rfq_no"],
                    "date": formatted_date,
                    "po_no": item["po_no"],
                    "supplier": item["supplier__name"],
                    "project": (item["rfq__project_name"] or "" ),
                    "made_by": item["made_by__first_name"] + " " + item["made_by__last_name"],
                    "approved_by": (item["approved_by__first_name"] or "") + " " +(item["approved_by__last_name"] or ""),
                    "remarks": (item["remarks"] or ""),
                    "total_amount": item["total_amount"],
                    "is_po_closed": item["is_po_closed"],
                    "is_approved": item["is_approved"],
                    "rfq_id": item["rfq"],
                    "is_resale": item["is_resale"]
                }
            data.append(poData)
        return JsonResponse({
                "status": 200,
                "success": True,
                "data": data,
                "total_page_number": poFinalData.paginator.num_pages
            }, status=status.HTTP_200_OK)

class ProjectView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        print(request.data)
        serializer = ProjectsSerializer(data=request.data)
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
        if query is None:
            projects = Projects.objects.all()
        else:
            try:
                projects = Projects.objects.filter(name__icontains=query)
            except Exception as e:
                return Response({
                    "status": 200,
                    "success": True,
                    "message": "Data not found",
                    "error": e
                })
        projects = projects.order_by('name')
        data = [{ 'id': project.id,
                'name': project.name,
                'address': project.address,
                'state': project.state,
                'city': project.city,
                'gst': project.gst,
                'pincode': project.pincode,
                'contact_person_name': project.contact_person_name,
                'contact_person_phone': project.contact_person_phone
                } for project in projects]
        
        return Response({
            "status": 200,
            "success": True,
            "message": "successfull GET request",
            "data": data
        })
    
class ExcelExportView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request):
        id = request.user.id
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
            
        query_set = PurchaseOrder.objects.filter(prepared_by = id)
        if from_date and to_date is not None:
            query_set = query_set.filter(created_at__date__range=[from_date, to_date])

        query_set = query_set.order_by('created_at')

        query_set.values(
            'created_at',
            'is_resale',
            'is_project',
            'po_no',
            'rfq__no'
        )