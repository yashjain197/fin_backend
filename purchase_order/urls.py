from django.urls import path
from .views import GeneratePO, FetchAllPO, FetchPOPdf, POView, POApprovalView, FetchPOGeneratedRFQ, ProjectView

urlpatterns = [
      path('generate-po/',GeneratePO.as_view()),
      path('fetch-all-po/',FetchAllPO.as_view()),
      path('fetch-po-pdf/',FetchPOPdf.as_view()),
      path('fetch-po-id/',POView.as_view()),
      path('update-po/',POView.as_view()),
      path('po-approval/',POApprovalView.as_view()),
      path('fetch-po-generated-rfq/',FetchPOGeneratedRFQ.as_view()),
      path('project/',ProjectView.as_view()),
]
