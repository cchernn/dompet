from rest_framework import serializers
from .models import Expenditure

class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = ["id", "date", "name", "location", "amount", "currency", "type", "payment_method", "user"]