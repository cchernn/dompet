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

def index(request):
    template_path = "BudgetTrack/index.html"
    return render(request, template_path, {})

def filter(request):
    columns_to_display = [
        "id",
        "date",
        "name",
        "location",
        "amount",
        "currency",
        "type",
        "payment_method",
        "user",
    ]
    params = list(request.GET.items())
    template_path = "BudgetTrack/list.html"
    df = pd.DataFrame(Expenditure.objects.order_by("-id").all().values())
    df = df[columns_to_display]
    for key,value in params:
        if key in df.columns:
            if key == 'date':
                df = df[df[key].astype(str) == value]
            else:
                df = df[df[key] == value]
            
    context = {
        "data": df
    }
    return render(request, template_path, context)

def detail(request, id):
    template_path = "BudgetTrack/detail.html"
    object = get_object_or_404(Expenditure, id=id)
    context = {
        "expenditure": object
    }
    return render(request, template_path, context)

def add(request):
    if request.method == "POST":
        form = ExpenditureForm(request.POST)
        if form.is_valid():
            form.save()
        context = {}
        return redirect("list")
    else:
        template_path = "BudgetTrack/add.html"
        form = ExpenditureForm()
        context = {
            "form": form
        }
        return render(request, template_path, context)

def edit(request, id):
    if request.method == "POST":
        object = get_object_or_404(Expenditure, id=id)
        form = ExpenditureForm(request.POST, instance=object)
        if form.is_valid():
            form.save()
        context = {}
        return redirect("list")
    else:
        template_path = "BudgetTrack/edit.html"
        object = get_object_or_404(Expenditure, id=id)
        form = ExpenditureForm(instance=object)
        context = {
            "object": object,
            "form": form
        }
        return render(request, template_path, context)

def delete(request, id):
    object = get_object_or_404(Expenditure, id=id)
    object.delete()
    return redirect("list")