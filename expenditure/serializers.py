from rest_framework import serializers
from .models import Expenditure, ExpenditureGroup
from .services import ExpenditureDataClass, ExpenditureGroupDataClass
from django.http import QueryDict

class ExpenditureSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    groupname = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = Expenditure
        fields = ["id", "date", "name", "location", "amount", "currency", "type", "payment_method", "user", "group", "username", "groupname", "category", "attachment", "inserted_at", "updated_at"]
        read_only_fields = ["id", "user", "group", "username", "groupname"]

    def to_internal_value(self, data):
        if self.partial:
            if isinstance(data, QueryDict):
                data = data.dict()
            for field,value in self.instance.__dict__.items():
                if field not in data.keys():
                    data[field] = value
        data = super().to_internal_value(data)

        return ExpenditureDataClass(**data)

class ExpenditureGroupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = ExpenditureGroup
        fields = ["id", "name", "owner", "username", "inserted_at", "updated_at"]
        read_only_fields = ["id", "owner", "username"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        return ExpenditureGroupDataClass(**data)