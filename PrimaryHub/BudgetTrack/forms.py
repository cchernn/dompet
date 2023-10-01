from django.forms import ModelForm
from .models import Expenditure

class ExpenditureForm(ModelForm):
    class Meta:
        model = Expenditure
        fields = ["date", "name", "location", "amount", "currency", "type", "payment_method", "user"]