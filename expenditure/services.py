import dataclasses
import datetime

from .models import Expenditure, ExpenditureGroup
from user.services import UserDataClass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import Expenditure, ExpenditureGroup
    from user.models import User

from django.shortcuts import get_object_or_404
from rest_framework import exceptions

@dataclasses.dataclass
class ExpenditureDataClass:
    user: UserDataClass = None
    date: datetime.datetime = None
    name: str = None
    location: str = ""
    amount: float = 0
    currency: str = "MYR"
    type: str = ""
    payment_method: str = ""
    group: int = None
    inserted_at: datetime.datetime = None
    updated_at: datetime.datetime = None
    id: int = None
    
    @classmethod
    def from_instance(cls, expenditure: "Expenditure") -> "ExpenditureDataClass":
        return cls(
            id=expenditure.id,
            date=expenditure.date,
            name=expenditure.name,
            location=expenditure.location,
            amount=expenditure.amount,
            currency=expenditure.currency,
            type=expenditure.type,
            payment_method=expenditure.payment_method,
            user=expenditure.user,
            group=expenditure.group,
            inserted_at=expenditure.inserted_at,
            updated_at=expenditure.updated_at,
        )

def create_expenditure(group_id: int, user: "User", expendituredc: "ExpenditureDataClass") -> "ExpenditureDataClass":
    instance = Expenditure.objects.create(
        date=expendituredc.date,
        name=expendituredc.name,
        location=expendituredc.location,
        amount=expendituredc.amount,
        currency=expendituredc.currency,
        type=expendituredc.type,
        payment_method=expendituredc.payment_method,
        user=user,
        group_id=group_id,
    )
    return ExpenditureDataClass.from_instance(expenditure=instance)

def get_expenditure(group_id: int) -> list["ExpenditureDataClass"]:
    group = get_object_or_404(ExpenditureGroup, pk=group_id)
    expenditure = Expenditure.objects.filter(group=group.id)

    return [ExpenditureDataClass.from_instance(ex) for ex in expenditure]

def get_expenditure_detail(group_id: int, expenditure_id: int) -> "ExpenditureDataClass":
    group = get_object_or_404(ExpenditureGroup, pk=group_id)
    expenditure = get_object_or_404(Expenditure, pk=expenditure_id, group=group.id)

    return ExpenditureDataClass.from_instance(expenditure=expenditure)

def delete_expenditure(user: "User", group_id: int, expenditure_id: int) -> "ExpenditureDataClass":
    group = get_object_or_404(ExpenditureGroup, pk=group_id)
    expenditure = get_object_or_404(Expenditure, pk=expenditure_id, group=group.id)

    if expenditure.user.id != user.id:
        raise exceptions.PermissionDenied("Invalid User")

    expenditure.delete()

def update_expenditure(user: "User", group_id: int, expenditure_id: int, expenditure_data: "ExpenditureDataClass") -> "ExpenditureDataClass":
    group = get_object_or_404(ExpenditureGroup, pk=group_id)
    expenditure = get_object_or_404(Expenditure, pk=expenditure_id, group=group.id)

    if expenditure.user.id != user.id:
        raise exceptions.PermissionDenied("Invalid User")

    expenditure.date = expenditure_data.date
    expenditure.name = expenditure_data.name
    expenditure.location = expenditure_data.location
    expenditure.amount = expenditure_data.amount
    expenditure.currency = expenditure_data.currency
    expenditure.type = expenditure_data.type
    expenditure.payment_method = expenditure_data.payment_method

    expenditure.save()

    return ExpenditureDataClass.from_instance(expenditure=expenditure)

@dataclasses.dataclass
class ExpenditureGroupDataClass:
    name: str = None
    user: UserDataClass = None
    id: int = None
    
    @classmethod
    def from_instance(cls, expenditure_group: "ExpenditureGroup") -> "ExpenditureGroupDataClass":
        return cls(
            id=expenditure_group.id,
            name=expenditure_group.name,
            user=expenditure_group.user,
            # inserted_at=expenditure_group.inserted_at,
            # updated_at=expenditure_group.updated_at,
        )

def create_expenditure_group(user: "User", expendituregroupdc: "ExpenditureGroupDataClass") -> "ExpenditureGroupDataClass":
    instance = ExpenditureGroup.objects.create(
        name=expendituregroupdc.name,
    )
    instance.user.set([user])
    return ExpenditureGroupDataClass.from_instance(expenditure_group=instance)

def get_expenditure_group(user: "User") -> list["ExpenditureGroupDataClass"]:
    ex_groups = ExpenditureGroup.objects.filter(user=user)

    return [ExpenditureGroupDataClass.from_instance(gr) for gr in ex_groups]

def get_expenditure_group_detail(user: "User", expenditure_group_id: int) -> "ExpenditureDataClass":
    ex_group = get_object_or_404(ExpenditureGroup, pk=expenditure_group_id)

    return ExpenditureGroupDataClass.from_instance(expenditure_group=ex_group)

def delete_expenditure_group(user: "User", expenditure_group_id: int) -> "ExpenditureDataClass":
    ex_group = get_object_or_404(ExpenditureGroup, pk=expenditure_group_id)

    ex_group.delete()

def update_expenditure_group(user: "User", expenditure_group_id: int, expenditure_group_data: "ExpenditureGroupDataClass") -> "ExpenditureGroupDataClass":
    ex_group = get_object_or_404(ExpenditureGroup, pk=expenditure_group_id)

    ex_group.name = expenditure_group_data.name

    ex_group.save()

    return ExpenditureGroupDataClass.from_instance(expenditure_group=ex_group)