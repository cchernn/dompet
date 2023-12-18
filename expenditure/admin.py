from django.contrib import admin

# Register your models here.

from .models import Expenditure, ExpenditureGroup

admin.site.register(Expenditure)
admin.site.register(ExpenditureGroup)