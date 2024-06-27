from celery import shared_task
from django.shortcuts import render
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.template.loader import render_to_string
from accounts.models import User
from nopa.models import NOPA, NOPAApproval
from nopa_backend import settings
from nopa_backend.utils import upload_document
from django.utils.html import strip_tags
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.db.models.functions import TruncMonth
from purchase_order.models import POApproval, PurchaseOrder
from rfq.models import RFQ, RFQApproval
from rfq.utils import getFormattedDate
from datetime import datetime, timedelta



class UploadDcumentView(APIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        if request.FILES:
            files = request.FILES.getlist('files')
            print(files)
            uploaded_links = upload_document(files)
        
            return JsonResponse({
                'status': 200,
                'success': True,
                'message': 'document uploaded successfully',
                'data': uploaded_links
                })
        else:
            return JsonResponse({
                'status': 400,
                'success': False,
                'message': 'Files not provided',
                'error': 'No files were provided'})

@shared_task      
def send_weekly_emails():
     for user in User.objects.all():
        body = ""
        mail_send = False

        if user.role == 'Manager' or user.role == 'SeniorManager':
            rfq = RFQApproval.objects.filter(requested_to=user.id, is_approved = False) 
            body = f"This is the remainder, {len(rfq)} Rfq is/are left for approvals."
            mail_send = True

        if user.role == 'AccountsTeam' or user.role == 'AccountsTeamManager':
            mail_send = True
            rfq = RFQ.objects.filter(status = 2, is_po_generated = False)
            body = f"This is the remainder, {len(rfq)} Rfq is/are approved but po is not yet generated."
            if user.role == 'AccountsTeamManager':
                po = POApproval.objects.filter(requested_to = user.id, is_approved = False)
                body = body + f"Also {len(po)} po is/are left for your approval."
            

        if user.role == 'Finance':
            mail_send = True
            po = PurchaseOrder.objects.filter(is_resale=False, is_po_closed = False)
            body = f"This is the remainder, {len(po)} PO is/are approved but nopa is not yet generated."
        
        nopaApproval = NOPAApproval.objects.filter(requested_to = user.id, is_approved = False)

        if len(nopaApproval) > 0:
            mail_send = True
            body += f"{len(nopaApproval)} NOPA is/are left for approval."

        body += "\nPlease Check!!"
        context = {
        'subject': "Reminder Mail Form Nopa Website",
        'body': body
        }
        html_content = render_to_string('email_template.html', context)
        text_content = strip_tags(html_content)
        print(text_content)
        # body = render_to_string('email_template.html', {'subject': subject, 'body': "Hello please ignore this email"})
        if mail_send:
            send_mail(
                context["subject"],
                text_content,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )        


def get_monthly_counts(model):
    monthly_data = {i: 0 for i in range(1, 13)}
    
    monthly_counts = (
        model
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .values('month', 'count')
    )

    for entry in monthly_counts:
        month = entry['month'].month
        monthly_data[month] = entry['count']
    
    return [monthly_data[i] for i in range(1, 13)]

def get_daily_counts(model):
    today = datetime.today()
    start_date = (today - timedelta(days=59)).date()  # Ensure we are working with date objects
    
    # Initialize the daily_data dictionary with date objects as keys
    daily_data = {start_date + timedelta(days=i): 0 for i in range(60)}
    
    daily_counts = (
        model
        .filter(created_at__date__gte=start_date)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .values('day', 'count')
    )
    
    print("Daily counts query result:", list(daily_counts))  # Debug print
    
    for entry in daily_counts:
        day = entry['day'].date()  # Convert datetime to date
        if day in daily_data:
            daily_data[day] = entry['count']
    
    print("Final daily data:", daily_data)  # Debug print
    
    return [daily_data[start_date + timedelta(days=i)] for i in range(60)]
# def get_latest_entries(model):
#     return list(model.objects.order_by('-created_at')[:10].values())

class DashboardView(APIView):
    permission_classes = (IsAuthenticated, )
    def get(self, request):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        purchaser = request.query_params.get("purchaser")
        project = request.query_params.get("project")
        department = request.query_params.get("department")
        type = request.query_params.get("type")
        graph_data = request.query_params.get("graph_data")
        

        RFQ_STATUS_DISPLAY = dict(RFQ.STATUS_CHOICES)
        PO_STATUS_DISPLAY = dict(PurchaseOrder.STATUS_CHOICES)
        NOPA_STATUS_DISPLAY = dict(NOPA.STATUS_CHOICES)

        total_rfq_made = 0
        total_po_made = 0
        total_nopa_made = 0

        total_rfq_pending_for_approval = 0
        total_po_pending_for_approval = 0
        total_nopa_pending_for_approval = 0

        total_po_pending = 0
        total_nopa_pending = 0

        rfq = RFQ.objects.all()
        po = PurchaseOrder.objects.all()
        nopa = NOPA.objects.all()

    
        
        if from_date and to_date is not None:
            rfq = rfq.filter(created_at__date__range=[from_date, to_date])
            po = po.filter(created_at__date__range=[from_date, to_date])
            nopa = nopa.filter(created_at__date__range=[from_date, to_date])
        elif from_date:
            rfq = rfq.filter(created_at__date__gte=from_date)
            po = po.filter(created_at__date__gte=from_date)
            nopa = nopa.filter(created_at__date__gte=from_date)
        elif to_date:
            rfq = rfq.filter(created_at__date__lte=to_date)
            po = po.filter(created_at__date__lte=to_date)
            nopa = nopa.filter(created_at__date__lte=to_date)
        
        if purchaser is not None:
            rfq = []
            po = po.filter(purchaser = purchaser)
            nopa = nopa.filter(po__purchaser = purchaser)
        
        if project:
            rfq = rfq.filter(project_name = project)
            po = po.filter(Q(project__name__icontains= project) | Q(contract_no__icontains= project) | Q(rfq__project_name__icontains= project))
            nopa = nopa.filter(
                Q(pre_nopa__po__project__name__icontains= project) | Q(pre_nopa__po__contract_no__icontains= project) | Q(pre_nopa__po__rfq__project_name__icontains= project)
            )

        if department:
            rfq = rfq.filter(
                requested_by__department = department
            )
            po = po.filter(
                rfq__requested_by__department = department, made_by__deaprtment = department
            )

            nopa = nopa.filter(
                Q(pre_nopa__po__rfq__requested_by__department = department) | Q(po__made_by__deaprtment = department) | Q(prepared_by__deaprtment = department)
            )

        if type:

            if type == 'project':
                rfq = []
                po = po.filter(
                    is_project = True
                )
                nopa = nopa.filter(
                    pre_nopa__po__is_project = True
                )
            if type == 'resale':
                rfq = []
                po = po.filter(
                    is_project = False, is_resale = True
                )

                nopa = nopa.filter(
                    pre_nopa__po__is_project = False,
                    pre_nopa__po__is_resale = True,
                )
            if type == 'normal':
                po = po.filter(
                    is_project = False, is_resale = False
                )

                nopa = nopa.filter(
                    pre_nopa__po__is_project = False, pre_nopa__po__is_resale = False
                )
                

        total_rfq_made = rfq.count()
        total_po_made = po.count()
        total_nopa_made = nopa.count()

        total_rfq_pending_for_approval = rfq.filter(status = 1).count()
        total_po_pending_for_approval = po.filter(status = 1).count()
        total_nopa_pending_for_approval = nopa.filter(status = 1).count()

        total_po_pending = rfq.filter(status = 2).count()
        total_nopa_pending = po.filter(status = 2).count()

        #Latest 10 Payments
        nopa_with_utr = nopa.filter(
            ~Q(utr_no=""), utr_no__isnull=False
            ).order_by('-updated_at')
        
        latest_nopa_with_utr = nopa_with_utr[:10]

        #Monthly/Daily Data
        if graph_data == 'monthly' or graph_data is None:
            rfq_counts = get_monthly_counts(rfq)
            po_counts = get_monthly_counts(po)
            nopa_counts = get_monthly_counts(nopa)
        elif graph_data == 'daily':
            rfq_counts = get_daily_counts(rfq)
            po_counts = get_daily_counts(po)
            nopa_counts = get_daily_counts(nopa)
        #for daily data
        end_date = datetime.today()
        start_date = (end_date - timedelta(days=59)).date()
        end_date = end_date.date()

        recent_rfq = rfq.order_by('-created_at')[:10].values(
            "id",
            "requested_by__first_name",
            "requested_by__last_name",
            "requested_by__department",
            "project_name",
            "rfq_no",
            "status",
            "created_at"
        )
        recent_po = po.order_by('-created_at')[:10].values(
            "id",
            "made_by__first_name",
            "made_by__last_name",
            "made_by__department",
            "po_no",
            "status",
            "created_at",
            "is_resale",
            "is_project",
            "project__name",
            "rfq__project_name",
            "contract_no",
            "supplier__name",
            "total_amount",
        )
        recent_nopa = nopa.order_by('-created_at')[:10].values(
            "id",
            "prepared_by__first_name",
            "prepared_by__last_name",
            "prepared_by__department",
            "nopa_no",
            "status",
            "created_at",
            "amount_paid",
            "pre_nopa__po__is_resale",
            "pre_nopa__po__is_project",
            "pre_nopa__po__project__name",
            "pre_nopa__po__rfq__project_name",
            "pre_nopa__po__contract_no",
            "pre_nopa__po__supplier__name",
            "pre_nopa__po__po_no"
        )

        recent_payment = latest_nopa_with_utr.values(
            "id",
            "prepared_by__first_name",
            "prepared_by__last_name",
            "prepared_by__department",
            "pre_nopa__po__supplier__name",
            "amount_paid",
            "created_at",
            "updated_at",
            "nopa_no",
            "utr_no",
            "pre_nopa__po__po_no",
            "invoice_no",
            "mode_of_payment",
            "status",
            "pre_nopa__po__is_resale",
            "pre_nopa__po__is_project",
            "pre_nopa__po__project__name",
            "pre_nopa__po__rfq__project_name",
            "pre_nopa__po__contract_no",
        )

        recent_rfq_data = []
        recent_po_data = []
        recent_nopa_data = []
        recent_payments_data = []

        for item in recent_rfq:
            data = {
                "id": item["id"],
                "name": item["requested_by__first_name"] + " " + item["requested_by__last_name"],
                "department": item["requested_by__department"],
                "project": item["project_name"],
                "status": RFQ_STATUS_DISPLAY.get(item["status"], "Unknown Status"),
                "rfq_no": item["rfq_no"],
                "date" : getFormattedDate(item["created_at"])
            }
            recent_rfq_data.append(data)

        for item in recent_po:
            if item["is_resale"]:
                if item["is_project"]:
                    project = item["project__name"]
                else:
                    project = item["contract_no"]
            else:
                project = item["rfq__project_name"]
            data = {
                "id": item["id"],
                "name": item["made_by__first_name"] + " " + item["made_by__last_name"],
                "department": item["made_by__department"],
                "po_no": item["po_no"],
                "project": project,
                "status": PO_STATUS_DISPLAY.get(item["status"], "Unknown Status"),
                "date" : getFormattedDate(item["created_at"]),
                "supplier": item["supplier__name"],
                "total_amount": item["total_amount"],
            }
            recent_po_data.append(data)

        for item in recent_nopa:
            if item["pre_nopa__po__is_resale"]:
                if item["pre_nopa__po__is_project"]:
                    project = item["pre_nopa__po__project__name"]
                else:
                    project = item["pre_nopa__po__contract_no"]
            else:
                project = item["pre_nopa__po__rfq__project_name"]
            data = {
                "id": item["id"],
                "name": item["prepared_by__first_name"] + " " + item["prepared_by__last_name"],
                "department": item["prepared_by__department"],
                "nopa_no": item["nopa_no"],
                "status": NOPA_STATUS_DISPLAY.get(item["status"], "Unknown Status"),
                "date" : getFormattedDate(item["created_at"]),
                "total_amount": item["amount_paid"],
                "project": project,
                "supplier": item["pre_nopa__po__supplier__name"],
                "po_no": item["pre_nopa__po__po_no"]
            }
            recent_nopa_data.append(data)

        for item in recent_payment:

            if item["pre_nopa__po__is_resale"]:
                if item["pre_nopa__po__is_project"]:
                    project = item["pre_nopa__po__project__name"]
                else:
                    project = item["pre_nopa__po__contract_no"]
            else:
                project = item["pre_nopa__po__rfq__project_name"]

            data = {
                "id": item["id"],
                "name": item["prepared_by__first_name"] + " " + item["prepared_by__last_name"],
                "department": item["prepared_by__department"],
                "nopa_no": item["nopa_no"],
                "status": NOPA_STATUS_DISPLAY.get(item["status"], "Unknown Status"),
                "date" : getFormattedDate(item["updated_at"]),
                "total_amount": item["amount_paid"],
                "project": project,
                "supplier": item["pre_nopa__po__supplier__name"],
                "po_no": item["pre_nopa__po__po_no"],
                "payment_mode": item["mode_of_payment"],
                "utr_no": item["utr_no"],
                "invoice_no": item["invoice_no"]
            }
            recent_payments_data.append(data)

        data = {
            "monthly_rfq_count": rfq_counts,
            "monthly_po_count": po_counts,
            "monthly_nopa_count": nopa_counts,
            "start_date": start_date,
            "end_date": end_date,
            "recent_rfq": recent_rfq_data,
            "recent_po": recent_po_data,
            "recent_nopa": recent_nopa_data,
            "recent_payment": recent_payments_data,
            "total_rfq_made": total_rfq_made,
            "total_po_made": total_po_made,
            "total_nopa_made": total_nopa_made,
            "total_payment_completed": nopa_with_utr.count(),
            "total_payment_pending": total_nopa_made - nopa_with_utr.count(),
            "total_rfq_pending_for_approval": total_rfq_pending_for_approval,
            "total_po_pending_for_approval": total_po_pending_for_approval,
            "total_nopa_pending_for_approval": total_nopa_pending_for_approval,
            "total_po_pending" : total_po_pending,
            "total_nopa_pending" : total_nopa_pending,
        }
        

        return JsonResponse({
            "status": 200,
            "success": True,
            "data": data
        })


