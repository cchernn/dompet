from django.shortcuts import render, redirect, get_object_or_404

# Create your views here.

from django.http import HttpResponse
from django.template import loader

from .models import Expenditure
from .forms import ExpenditureForm

from rest_framework import viewsets
from .serializers import ExpenditureSerializer

import pandas as pd

class ExpenditureView(viewsets.ModelViewSet):
    serializer_class = ExpenditureSerializer
    queryset = Expenditure.objects.all()
