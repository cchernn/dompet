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
from django.db.models import Sum, Count, Value, CharField
from django.db.models.functions import Concat, ExtractYear, ExtractMonth

@dataclasses.dataclass
class ExpenditureDataClass:
    user: UserDataClass = None
    date: datetime.datetime = None
    name: str = None
    location: str = ""
    amount: float = 0
    currency: str = "MYR"
    type: str = "spend"
    payment_method: str = ""
    group: int = None
    username: str = ""
    groupname: str = ""
    category: str = "others"
    attachment: str = ""
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
            username=expenditure.user.username,
            groupname=expenditure.group.name,
            category=expenditure.category,
            attachment=expenditure.attachment,
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
        category=expendituredc.category,
        attachment=expendituredc.attachment,
    )
    return ExpenditureDataClass.from_instance(expenditure=instance)

def get_expenditure(group_id: int) -> list["ExpenditureDataClass"]:
    group = get_object_or_404(ExpenditureGroup, pk=group_id)
    expenditure = Expenditure.objects.filter(group=group.id)
    expenditure = expenditure.order_by('-id')

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
    expenditure.category = expenditure_data.category
    expenditure.attachment = expenditure_data.attachment

    expenditure.save()

    return ExpenditureDataClass.from_instance(expenditure=expenditure)

@dataclasses.dataclass
class ExpenditureGroupDataClass:
    name: str = None
    users: UserDataClass = None
    owner: UserDataClass = None
    username: str = ""
    inserted_at: datetime.datetime = None
    updated_at: datetime.datetime = None
    id: int = None
    
    @classmethod
    def from_instance(cls, expenditure_group: "ExpenditureGroup") -> "ExpenditureGroupDataClass":
        return cls(
            id=expenditure_group.id,
            name=expenditure_group.name,
            users=expenditure_group.users,
            owner=expenditure_group.owner,
            username=expenditure_group.owner.username,
            inserted_at=expenditure_group.inserted_at,
            updated_at=expenditure_group.updated_at,
        )

def create_expenditure_group(user: "User", expendituregroupdc: "ExpenditureGroupDataClass") -> "ExpenditureGroupDataClass":
    instance = ExpenditureGroup.objects.create(
        name=expendituregroupdc.name,
        owner=user
    )
    instance.users.set([user])
    return ExpenditureGroupDataClass.from_instance(expenditure_group=instance)

def get_expenditure_group(user: "User") -> list["ExpenditureGroupDataClass"]:
    ex_groups = ExpenditureGroup.objects.filter(users=user)

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

def get_expenditure_summary(user: "User", group_id: int) -> dict:
    now = datetime.datetime.now()
    # prev_m = now - datetime.timedelta(days=7)
    # prev_y = now - datetime.timedelta(days=365)
    mtd = datetime.date(now.year, now.month, 1)
    ytd = datetime.date(now.year, 1, 1)

    expenditure = {}

    ex_data = Expenditure.objects.filter(
        group_id=group_id,
        type="spend",
    )

    ex_data_mtd = ex_data.filter(
        date__range=[mtd.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")]
    )

    ex_data_ytd = ex_data.filter(
        date__range=[ytd.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")]
    )

    expenditure['expenditure_total'] = ex_data.aggregate(
        total_spend = Sum("amount", default=0),
        total_items = Count("id"),
    )

    expenditure['expenditure_mtd'] = ex_data_mtd.aggregate(
        total_spend = Sum("amount", default=0),
        total_items = Count("id"),
    )

    expenditure['expenditure_ytd'] = ex_data_ytd.aggregate(
        total_spend = Sum("amount", default=0),
        total_items = Count("id"),
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data, group="user")
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data_mtd, group="user", suffix="_mtd")
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data_ytd, group="user", suffix="_ytd")
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data, group="category")
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data_mtd, group="category", suffix="_mtd")
    )

    expenditure.update(
        get_expenditure_summary_by_group(ex_data=ex_data_ytd, group="category", suffix="_ytd")
    )

    # expenditure['expenditure_by_date'] = ex_data.filter(
    #     date__range=[prev_m.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")]
    # ).values(
    #     "date"
    # ).order_by(
    #     "date"
    # ).annotate(
    #     total_spend = Sum("amount", default=0),
    #     total_items = Count("id"),
    # )

    # expenditure['expenditure_by_month'] = ex_data.filter(
    #     date__range=[prev_y.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")]
    # ).annotate(
    #     year_month = Concat(
    #         ExtractYear("date"),
    #         Value("-"),
    #         ExtractMonth("date", output_field=CharField()),
    #         output_field=CharField()
    #     )
    # ).values(
    #     "year_month"
    # ).order_by(
    #     "year_month"
    # ).annotate(
    #     total_spend = Sum("amount", default=0),
    #     total_items = Count("id"),
    # )

    return expenditure

def get_expenditure_summary_by_group(ex_data: Expenditure, group: str = "category", suffix: str = ""):
    result = {}
    expenditure_by_group = ex_data.values(
        group
    ).annotate(
        total_spend = Sum("amount", default=0),
        total_items = Count("id"),
    ).order_by(
        "-total_spend"
    )
    groups = [ex[group] for ex in expenditure_by_group[:10]]
    groups_others = []
    if len(expenditure_by_group) > 10:
        groups_others = [ex[group] for ex in expenditure_by_group[10:]]
        ex_others = {
            group: "others",
            "total_spend": sum(ex["total_spend"] for ex in expenditure_by_group[10:]),
            "total_items": sum(ex["total_items"] for ex in expenditure_by_group[10:])
        }
        expenditure_by_group = expenditure_by_group[:10] + [ex_others]
    result[f'expenditure_by_{group}{suffix}'] = expenditure_by_group

    expenditure_by_group_breakdown = {}
    for group_i in groups:
        expenditure_by_group_breakdown[group_i] = []
        expenditure_by_group_i = ex_data.filter(
            **{group:group_i}
        ).values(
            "name"
        ).annotate(
            total_spend = Sum("amount", default=0),
            total_items = Count("id")
        ).order_by(
            "-total_spend"
        )
        if expenditure_by_group_i:
            expenditure_by_group_i = expenditure_by_group_i[:5]
            expenditure_by_group_breakdown[group_i] = expenditure_by_group_i

    if len(groups_others) > 0:
        expenditure_by_group_breakdown["others"] = []
        expenditure_by_group_others = ex_data.filter(
            **{f"{group}__in":groups_others}
        ).values(
            "name"
        ).annotate(
            total_spend = Sum("amount", default=0),
            total_items = Count("id")
        ).order_by(
            "-total_spend"
        )
        if expenditure_by_group_others:
            expenditure_by_group_others = expenditure_by_group_others[:5]
            expenditure_by_group_breakdown["others"] = expenditure_by_group_others
    result[f"expenditure_by_{group}_breakdown{suffix}"] = expenditure_by_group_breakdown

    return result