from django.urls import path
from .views import  GenerateRFQ, FetchAllRFQ, RFQView, RFQPDFView, ApprovalView, RejectedView

urlpatterns = [
  path('generate-rfq/',GenerateRFQ.as_view()),
  path('fetch-all-rfq/',FetchAllRFQ.as_view()),
  path('fetch-rfq/', RFQView.as_view()),
  path('fetch-rfq-pdf/', RFQPDFView.as_view()),
  path('rfq-approval/', ApprovalView.as_view()),
  path('rfq-reject/', RejectedView.as_view()),
  path('rfq-revise/', RFQView.as_view()),
]
