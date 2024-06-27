from django.urls import path

from .views import VendorView, PurchaserView, GenerateNOPA, FetchAllNOPA, NopaApproval, NopaView, FetchNOPAPdf, GeneratePreNopa, FetchAllPreNopa, PreNopaView, ExcelExportView


urlpatterns = [
  path('vendors/',VendorView.as_view()),
  path('purchaser/',PurchaserView.as_view()),
  path('generate-nopa/',GenerateNOPA.as_view()),
  path('fetch-all-nopa/',FetchAllNOPA.as_view()),
  path('approval/',NopaApproval.as_view()),
  path('fetch-nopa-id/',NopaView.as_view()),
  path('fetch-nopa-pdf/',FetchNOPAPdf.as_view()),
  path('generate-pre-nopa/',GeneratePreNopa.as_view()),
  path('fetch-all-pre-nopa/',FetchAllPreNopa.as_view()),
  path('fetch-pre-nopa/',PreNopaView.as_view()),
  path('update-nopa/',NopaView.as_view()),
  path('export-report/',ExcelExportView.as_view()),
]