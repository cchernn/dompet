from django.urls import path

from . import apis

urlpatterns = [
    path("expenditures", apis.ExpenditureCreateAPI.as_view(), name="expenditure"),
    path("expenditures/<int:expenditure_id>", apis.ExpenditureRetrieveUpdateDeleteAPI.as_view(), name="expenditure_detail"),
    path("expendituregroup/<int:expenditure_group_id>/expenditures", apis.ExpenditureGroupCreateAPI.as_view(), name="expenditure_group"),
    path("expendituregroup/<int:expenditure_group_id>/expenditures/<int:expenditure_id>", apis.ExpenditureGroupRetrieveUpdateDeleteAPI.as_view(), name="expenditure_group")
]