from django.db import models
from django.conf import settings

# Create your models here.

class Expenditure(models.Model):
    date = models.DateField(verbose_name="Date")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="User")
    name = models.CharField(max_length=256, verbose_name="Name")
    location = models.CharField(max_length=256, verbose_name="Location")
    type = models.CharField(max_length=256, verbose_name="Type")
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0, verbose_name="Amount")
    currency = models.CharField(max_length=3, default="MYR", verbose_name="Currency")
    payment_method = models.CharField(max_length=256, verbose_name="Payment Method")
    inserted_at = models.DateTimeField(auto_now_add=True, verbose_name="Inserted At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        if self.type == "Expenditure":
            type_text = "spent"
        elif self.type == "Transfer":
            type_text = "transferred"
        elif self.type == "Received":
            type_text = "received"
        return f"{self.date}: {self.user.first_name} {type_text} {self.amount} for {self.name}, {self.location}"

