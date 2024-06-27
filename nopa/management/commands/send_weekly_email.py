from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from accounts.models import User
from nopa.models import NOPAApproval
from nopa_backend import settings
from nopa_backend.utils import upload_document
from django.utils.html import strip_tags

from purchase_order.models import POApproval, PurchaseOrder
from rfq.models import RFQ, RFQApproval

class Command(BaseCommand):
    help = 'Send weekly email'

    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            body = ""
            mail_send = False

            if user.role == 'Manager' or user.role == 'SeniorManager':
                rfq = RFQApproval.objects.filter(requested_to=user.id, is_approved = False)
                if len(rfq) > 0: 
                    body = f"This is the Reminder, {len(rfq)} Rfq is/are left for approvals."
                    mail_send = True

            if user.role == 'AccountsTeam' or user.role == 'AccountsTeamManager':
                rfq = RFQ.objects.filter(status = 2, is_po_generated = False)
                if len(rfq) > 0:
                    body = f"This is the Reminder, {len(rfq)} Rfq is/are approved but po is not yet generated."
                    mail_send = True
                if user.role == 'AccountsTeamManager':
                    po = POApproval.objects.filter(requested_to = user.id, is_approved = False)
                    if len(po) > 0:
                        body = body + f"Also {len(po)} po is/are left for your approval."
                        mail_send = True
                

            if user.role == 'Finance':
                if len(po) > 0:
                    mail_send = True
                    po = PurchaseOrder.objects.filter(is_resale=False, is_po_closed = False)
                    body = f"This is the Reminder, {len(po)} PO is/are approved but nopa is not yet generated."
            
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
            # body = render_to_string('email_template.html', {'subject': subject, 'body': "Hello please ignore this email"})
            if mail_send:
                send_mail(
                    context["subject"],
                    text_content,
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )

        self.stdout.write(self.style.SUCCESS('Successfully sent weekly email'))