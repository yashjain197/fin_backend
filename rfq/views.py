from datetime import datetime
from django.shortcuts import render
from django.core.paginator import Paginator
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.template.loader import get_template
from weasyprint import HTML
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
import threading
from accounts.models import User
from nopa_backend import settings

from .serializer import RFQApprovalSerializer, RFQSerializer
from .utils import generate_rfq_no, getFormattedDate
from .models import RFQ, RFQApproval
# Create your views here.
def generate_rfq_pdf(id):
    try:
        data = RFQ.objects.get(id=id)
    except Exception as e:
        output = {
                "success": False,
                "status":404,
                "message": "RFQ not found"
            }
        return Response(output)
    date_string = str(data.created_at)
    date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f%z")
    formatted_date = date_obj.strftime("%d-%m-%Y")
    context = {
                "refrence_number": data.rfq_no,
                "date": formatted_date,
                "requested_by": data.requested_by.first_name.title() + " " + data.requested_by.last_name.title(),
                "department": data.requested_by.department,
                "requested_by_contact" : data.requested_by.contact_number,
                "requested_by_email" : data.requested_by.email,
                "priority" : data.priority,
                "project_name" : data.project_name,
                "description" : data.description,
                "material_category" : data.material_category,
                "item_list": data.item_list,
                "is_attachments_available": data.attachments,
                "resale_details": data.resale_details,
                "made_by": data.requested_by.first_name.title() + " " + data.requested_by.last_name.title(),
                "purchaser": data.purchaser.id
                }
    if data.approved_by is not None:
        context["approved_by"] = data.approved_by.first_name.title() + " " + data.approved_by.last_name.title()
        context["approved_by_date"] = data.approved_by_date
    else:
        context["approved_by"] = ""
        context["approved_by_date"] = ""

    if data.approved_by_manager is not None:
        context["approved_by_manager"] = data.approved_by_manager.first_name.title() + " " + data.approved_by_manager.last_name.title()
        context["approved_by_manager_date"] = data.approved_by_manager_date
    else:
        context["approved_by_manager"] = ""
        context["approved_by_manager_date"] = ""
    
    html_string1 = get_template('rfq.html').render(context)
    pdf_file = HTML(string=html_string1).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rfq.pdf"'
    return response

class GenerateRFQ(APIView):
    permission_classes= (IsAuthenticated, )

    def post(self, request):
        data = request.data
     
        data["requested_by"] = request.user.id

        for i, item in enumerate(data['item_list']):
            item['id'] = i + 1
            item['is_po_generated'] = False
        serializer = RFQSerializer(data=data)
        if serializer.is_valid():
            data = serializer.save()
            data = RFQ.objects.get(id = data.id)
            data.rfq_no = generate_rfq_no(data.id)
            data.save()
            #send for approval
            approval_data = {
                    "requested_to": request.data.get('approval_manager_id'),
                    "rfq_id": data.id
                }
            approval_serializer = RFQApprovalSerializer(data = approval_data)
            if approval_serializer.is_valid():
                approval_serializer.save()
                email_from = settings.EMAIL_HOST_USER
                email_to = User.objects.get(id = request.data.get('approval_manager_id')).email
                subject = "Reminder Mail"
                message = f"An RFQ with the number {data.rfq_no} has been created and is awaiting your approval. Please review it at your earliest convenience."
                recipient_list = [email_to,]
                # send_mail(subject, message, email_from, recipient_list)
                threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()
                
            else:
                print(approval_serializer.errors)
           
        return generate_rfq_pdf(data.id)
    
class FetchAllRFQ(APIView):
    permission_classes= (IsAuthenticated, )

    def get(self, request):
        page = request.query_params.get("page")
        rfq_no = request.query_params.get("rfq_no")
        deaprtment = request.query_params.get("department")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        project_name = request.query_params.get("project_name")
        status = request.query_params.get("status")
        id = request.user.id
        role = request.user.role
        query = request.query_params.get("query")   
        if role == 'AccountsTeam' or role == 'AccountsTeamManager' or role == 'Admin' or role == 'Finance':
            rfq = RFQ.objects.all().order_by("-created_at")
        else:
            rfq = RFQ.objects.filter(requested_by=id).order_by("-created_at")

        if rfq_no:
            rfq = rfq.filter(rfq_no__icontains=rfq_no)

        if status:
            rfq  = rfq.filter(status__iexact=status)
        
        if project_name:
             rfq  = rfq.filter(project_name__iexact=project_name)

        if query:
            search_filter = Q(rfq_no__icontains=query) | Q(requested_by__first_name__icontains=query) | Q(requested_by__last_name__icontains=query)
            rfq = rfq.filter(search_filter)
        
        if from_date and to_date is not None:
            rfq = rfq.filter(created_at__date__range=[from_date, to_date])
        elif from_date:
            rfq = rfq.filter(created_at__date__gte=from_date)
        elif to_date:
            rfq = rfq.filter(created_at__date__lte=to_date)
            
        # if search_query:
        #     rfq = rfq.filter(
        #         Q(rfq_no__iexact=search_query) |
        #         Q(priority__iexact=search_query) |
        #         Q(requested_by__first_name__icontains=search_query) |  
        #         Q(requested_by__last_name__icontains=search_query) |  
        #         Q(material_category__iexact=search_query) |
        #         Q(requested_by__department__iexact=search_query)
        #     )
        # if is_po_generated:
        #     rfq.filter(is_po_generated = True)
        # Apply date filter
        # if from_date and to_date:
        #     from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        #     # # from_date = from_date.strftime("%Y-%m-%d")
        #     # print(from_date)
        #     to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        #     # print(to_date)
        #     # to_date = to_date.strftime("%Y-%m-%d")

        #     rfq = rfq.filter(created_at__gte=from_date, created_at__lte=to_date)
        rfq.order_by('created_at')
        paginator = Paginator(rfq, 30)
        rfqFinalData = paginator.get_page(page)
        
        if len(rfq) == 0:
                return Response({
                    "status": 404,
                    "success": False,
                    "message": "No RFQ found",
                    "data": []
                })
        
        data = []
        for rfqDetails in rfqFinalData:
            # date_string = str(rfqDetails.created_at)
            # date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f%z")
            formatted_date = getFormattedDate(rfqDetails.created_at)
            rfqdata = {
                "id": rfqDetails.id,
                "requested_by_name": rfqDetails.requested_by.first_name + " " + rfqDetails.requested_by.last_name,
                "requested_by_phone" : rfqDetails.requested_by.contact_number,
                "requested_by_email" : rfqDetails.requested_by.email,
                "requested_by_department" : rfqDetails.requested_by.department,
                "requested_to_name": rfqDetails.requested_to.first_name + " " + rfqDetails.requested_to.last_name ,
                "requested_to_phone" : rfqDetails.requested_to.contact_number,
                "requested_to_email" : rfqDetails.requested_to.email,
                "priority": rfqDetails.priority,
                "project_name" : rfqDetails.project_name,
                "date": formatted_date,
                "description": rfqDetails.description,
                "material_category": rfqDetails.material_category,
                "attachments": rfqDetails.attachments,
                "attachment_list": rfqDetails.attachment_list,
                "rfq_no": rfqDetails.rfq_no,
                "is_rfq_closed": rfqDetails.is_rfq_closed,
                "status": rfqDetails.get_status_display(),
                "is_only_rfq": rfqDetails.is_only_rfq
                # "approved_by": rfqDetails.approved_by,
                # "is_manager_approval": rfqDetails.is_manager_approval,
                # "approved_by_manager": rfqDetails.approved_by_manager
            }
            
            try:
                if rfqDetails.approved_by is not None:
                    rfqdata["approved_by"] = rfqDetails.approved_by.first_name + " " + rfqDetails.approved_by.last_name
                else:
                     rfqdata["approved_by"] = ""
                if rfqDetails.is_manager_approval is not None:
                    rfqdata["is_manager_approval"] = rfqDetails.is_manager_approval
                else:
                    rfqdata["is_manager_approval"] = ""
                if rfqDetails.approved_by_manager is not None:
                    rfqdata["approved_by_manager"] = rfqDetails.approved_by_manager.first_name + " " + rfqDetails.approved_by_manager.last_name
                else:
                    rfqdata["approved_by_manager"] = ""
            except Exception as e:
                print(e)
                data["approved_by"] = None
                data["is_manager_approval"] = None
                data["approved_by_manager"] = None
            
            data.append(rfqdata)
        return JsonResponse({
                "status": 200,
                "success": True,
                "data": data,
                "total_page_number": rfqFinalData.paginator.num_pages
            })
    
class RFQView(APIView):
    permission_classes= (IsAuthenticated, )

    def get(self, request):
        id = request.query_params.get("id")
        if id == None:
            return Response({
                "success": False,
                "message": "id not provided"
            })

        try:
                rfq = RFQ.objects.get(id=id)
        except Exception as e:
            print(e)
            return Response({
                "status": 400,
                "success": False,
                "error": e
            }, status=status.HTTP_200_OK)
        
        formatted_date = getFormattedDate(rfq.created_at)

        rfqdata = {
                "id": rfq.id,
                "requested_by_name": rfq.requested_by.first_name + " " + rfq.requested_by.last_name,
                "requested_by_phone" : rfq.requested_by.contact_number,
                "requested_by_email" : rfq.requested_by.email,
                "requested_by_department" : rfq.requested_by.department,
                "requested_to_name": rfq.requested_to.first_name + " " + rfq.requested_to.last_name ,
                "requested_to_phone" : rfq.requested_to.contact_number,
                "requested_to_email" : rfq.requested_to.email,
                "priority": rfq.priority,
                "project_name" : rfq.project_name,
                "date": formatted_date,
                "description": rfq.description,
                "material_category": rfq.material_category,
                "attachments": rfq.attachments,
                "attachment_list": rfq.attachment_list,
                "rfq_no": rfq.rfq_no,
                "item_list": rfq.item_list,
                "purchaser_name": rfq.purchaser.name
            }
        
        return Response({
             "success": True,
             "status": 200,
             "message": "Successful GET request",
             "data": rfqdata
        })
    
    def post(self, request):
        data = request.data
     
        data["requested_by"] = request.user.id
        old_rfq = RFQ.objects.get(id = data["rfq_id"])
        revision = old_rfq.revision
        for i, item in enumerate(data['item_list']):
            item['id'] = i + 1
            item['is_po_generated'] = False
        serializer = RFQSerializer(data=data)
        if serializer.is_valid():
            data = serializer.save()
            data = RFQ.objects.get(id = data.id)
            data.revision = revision + 1
            rfq = old_rfq.rfq_no
            if data.revision > 1:
                last_slash_index = rfq.rfind("/")
                if last_slash_index != -1:  # Check if '/' was found
                    rfq = rfq[:last_slash_index]
                    data.rfq_no = rfq + "/" + str(data.revision)
            else:       
                data.rfq_no = rfq + "/" + str(data.revision)

            data.save()
            #send for approval
            approval_data = {
                    "requested_to": request.data.get('approval_manager_id'),
                    "rfq_id": data.id
                }
            approval_serializer = RFQApprovalSerializer(data = approval_data)
            if approval_serializer.is_valid():
                approval_serializer.save()
            else:
                print(approval_serializer.errors)
           
        return generate_rfq_pdf(data.id)
    
class RFQPDFView(APIView):
    permission_classes= (IsAuthenticated, )
    def get(self, request):
        id = request.query_params.get("id")
        if id is None:
            return Response({
                "success": False,
                "message": "please provide id",
                "status": 400
            })
        return generate_rfq_pdf(id)

class ApprovalView(APIView):
    permission_classes= (IsAuthenticated, )
    def get(self, request):
        page = request.query_params.get("page")
        id = request.user.id
        approvals = RFQApproval.objects.filter(requested_to=id, is_approved=False)
        paginator = Paginator(approvals, 30)
        finalData = paginator.get_page(page)
        data = []
        for item in finalData:
            approval_data = {
                "id": item.id,
                "rfq_id": item.rfq_id.id,
                "rfq_no": item.rfq_id.rfq_no,
                "requested_by": item.rfq_id.requested_by.first_name + " " + item.rfq_id.requested_by.last_name,
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
        rfq_id = data["rfq_id"]
        approval_id = data["id"]
        is_manager_approval = data.get('is_manager_approval')

        if is_manager_approval is None:
            is_manager_approval = False
        
        approvals = RFQApproval.objects.get(id = approval_id)
        if approvals.is_approved:
            return Response({
                "success": False,
                "message": "RFQ Already Approved",
                "status": 400,
            })
        rfq = RFQ.objects.get(id = rfq_id)
        date = datetime.now().strftime('%Y-%m-%d')
        if request.user.role == 'Manager' or request.user.role == 'Admin':
            user = User.objects.get(id=request.user.id)
            rfq.approved_by = user
            rfq.approved_by_date = date
            rfq.is_manager_approval = is_manager_approval
            if is_manager_approval:
                data = {
                    "requested_to":data["approval_manager_id"],
                    "rfq_id": rfq_id
                }
                serilizer = RFQApprovalSerializer(data=data)
                if serilizer.is_valid():
                    serilizer.save()
                    email_from = settings.EMAIL_HOST_USER
                    email_to = User.objects.get(id = request.data.get('approval_manager_id')).email
                    subject = "Reminder Mail"
                    message = f"An RFQ with the number {rfq.rfq_no} has been created and is awaiting your approval. Please review it at your earliest convenience."
                    recipient_list = [email_to,]
                    threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()
            else:
                rfq.status = 2
        elif request.user.role == 'SeniorManager':
            is_manager_approval = False

            if rfq.approved_by is not None:

                rfq.approved_by_manager = User.objects.get(id=request.user.id)
                rfq.approved_by_manager_date = date
                rfq.status = 2
            else:
                rfq.approved_by = User.objects.get(id=request.user.id)
                rfq.approved_by_date = date
                rfq.is_manager_approval = False
                rfq.status = 2
        elif request.user.role == 'AccountsTeamManager':
            is_manager_approval = False
            rfq.approved_by = User.objects.get(id=request.user.id)
            rfq.approved_by_date = date
            rfq.status = 2
            rfq.is_manager_approval = False

        else:
            return Response({
                "success": False,
                "message": "only manager can approve RFQ",
                "status": 400,
            })

        rfq.save()

        if not is_manager_approval:
                email_from = settings.EMAIL_HOST_USER
                email_to = list(User.objects.filter(role__in =['AccountsTeam', 'AccountsTeamManager']).values_list('email', flat=True))
                subject = "Reminder Mail"
                message = f"An RFQ with the number {rfq.rfq_no} has been Approved and is awaiting to create Purchase Order. Please review it at your earliest convenience."
                recipient_list = email_to
                threading.Thread(target=send_mail, args=(subject, message, email_from, recipient_list)).start()

        approvals.is_approved = True
        approvals.is_active=False
        approvals.save()

        if is_manager_approval == True:
             return Response({
                "success": True,
                "message": "RFQ sent for approval",
                "status": 200,
            })

        return Response({
                "success": True,
                "message": "RFQ Approved",
                "status": 200,
            })

class RejectedView(APIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        data = request.data
        approval = RFQApproval.objects.get(id = data["id"])
        approval.delete()
        if request.user.role == 'Admin' or request.user.role == 'Manager' or request.user.role == 'SeniorManager':
            try:
                rfq = RFQ.objects.get(id = data['rfq_id'])
            except:
                return Response({
                    "status": 400,
                    "success": True,
                    "message": "Rfq Not Found"
                })
            rfq.is_rfq_rejected = True
            rfq.rejected_by = User.objects.get(id = request.user.id)
            rfq.status = 8
            rfq.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "rfq successfully rejected"
            })
        else:
            return Response({
                "status": 400,
                "success": True,
                "message": "rfq can be rejected by only managers"
            })