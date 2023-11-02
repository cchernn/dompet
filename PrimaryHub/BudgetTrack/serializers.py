from rest_framework import serializers
from .models import Expenditure
from .services import ExpenditureDataClass
from django.http import QueryDict

class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = ["id", "date", "name", "location", "amount", "currency", "type", "payment_method", "user", "inserted_at", "updated_at"]
        read_only_fields = ["id"]

    def to_internal_value(self, data):
        if self.partial:
            if isinstance(data, QueryDict):
                data = data.dict()
            for field,value in self.instance.__dict__.items():
                if field not in data.keys():
                    data[field] = value
        data = super().to_internal_value(data)

        return ExpenditureDataClass(**data)
        