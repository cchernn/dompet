from django.db import models
import datetime

# Create your models here.

class Expenditure(models.Model):
    date = models.DateField()
    user = models.CharField(max_length=32)
    name = models.CharField(max_length=256)
    location = models.CharField(max_length=256)
    type = models.CharField(max_length=256)
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="MYR")
    payment_method = models.CharField(max_length=256)
    inserted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.type == "Expenditure":
            type_text = "spent"
        elif self.type == "Transfer":
            type_text = "transferred"
        elif self.type == "Received":
            type_text = "received"
        return f"{self.date}: {self.user} {type_text} {self.amount} for {self.name}, {self.location}"

