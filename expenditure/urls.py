from django.urls import path

from . import apis

urlpatterns = [
    path("expendituregroups/<int:expenditure_group_id>/expenditures", apis.ExpenditureCreateAPI.as_view(), name="expenditure"),
    path("expendituregroups/<int:expenditure_group_id>/expenditures/<int:expenditure_id>", apis.ExpenditureRetrieveUpdateDeleteAPI.as_view(), name="expenditure_detail"),
    path("expendituregroups", apis.ExpenditureGroupCreateAPI.as_view(), name="expenditure_group"),
    path("expendituregroups/<int:expenditure_group_id>", apis.ExpenditureGroupRetrieveUpdateDeleteAPI.as_view(), name="expenditure_group"),
    path("expendituregroups/<int:expenditure_group_id>/summary", apis.ExpenditureSummaryAPI.as_view(), name="summary")
]