from django.urls import path

from . import apis

urlpatterns = [
    path("expenditures/", apis.ExpenditureCreateAPI.as_view(), name="expenditure"),
    path("expenditures/<int:expenditure_id>", apis.ExpenditureRetrieveUpdateDeleteAPI.as_view(), name="expenditure_detail")
]