from django.db import models
from django.conf import settings

# Create your models here.

class ExpenditureGroup(models.Model):
    name = models.CharField(max_length=256, verbose_name="Name")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owner", verbose_name="Owner")
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="users", verbose_name="Users")
    inserted_at = models.DateTimeField(auto_now_add=True, verbose_name="Inserted At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        return self.name

class Expenditure(models.Model):
    date = models.DateField(verbose_name="Date")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="User")
    name = models.CharField(max_length=256, verbose_name="Name")
    location = models.CharField(max_length=256, verbose_name="Location", blank=True)
    type = models.CharField(max_length=256, default="spend", verbose_name="Type")
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0, verbose_name="Amount")
    currency = models.CharField(max_length=3, default="MYR", verbose_name="Currency")
    payment_method = models.CharField(max_length=256, verbose_name="Payment Method", blank=True)
    group = models.ForeignKey(ExpenditureGroup, on_delete=models.CASCADE, verbose_name="Group")
    inserted_at = models.DateTimeField(auto_now_add=True, verbose_name="Inserted At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        if self.type == "spend":
            type_text = "spent"
        elif self.type == "transfer":
            type_text = "transferred"
        elif self.type == "receive":
            type_text = "received"
        return f"{self.date}: {self.user.username} {type_text} {self.amount} for {self.name}"

