from django.shortcuts import render, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.utils import timezone
from .form import IeSysForm
from .models import IeSys
import pandas as pd
import plotly.express as px
# Create your views here.

def index(request):
    """编写收支系统的主页视图"""
    return render(request, 'IESys_/index.html')

def ie(request):
    """编写主页中跳转收支页面的视图"""
    return render(request, 'IESys_/ie.html')

def sta(request):
    """编写主页中统计页面的视图"""
    return render(request, 'IESys_/sta.html')

def income(request):
    """编写收支页面的收入的视图"""
    if request.method != "POST":
        form = IeSysForm()
    else:
        form = IeSysForm(data=request.POST)
        if form.is_valid():
            print("表单是合理的")
            form.save()
            messages.success(request, '支出添加成功！')
            return redirect('IESys_:income')
        print("表单是不合理的")
    context = {'form': form}
    return render(request, 'IESys_/income.html', context)

def expenditure(request):
    """"编写支出页面的支出视图"""
    if request.method != "POST":
        form = IeSysForm()
    else:
        form = IeSysForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "收入添加成功！")
            return redirect('IESys_:expenditure')
    context = {'form': form}
    return render(request, 'IESys_/expenditure.html', context)

def income_detail(request):
    """编写收入的详细页面视图"""
    today = timezone.now().date()
    objects = IeSys.objects.filter(date=today)
    if objects:
        data = {}
        for object in objects:
            income = object.income
            amount = object.income_amount
            if amount:
                data[income] = data.get(income, 0) + amount
        fig = px.pie(values=data.values(), names=data.keys(), title='收入构成')
        fig = fig.to_html(full_html=False)
        context = {'flag': 1, 'fig': fig}
        return render(request, 'IESys_/income_detail.html', context)
    else:
        context = {'flag': 0}
        return render(request, 'IESys_/income_detail.html', context)
    
def expenditure_detail(request):
    """"编写收入的详细页面视图"""
    today = timezone.now().date()
    objects = IeSys.objects.filter(date=today)
    if objects:
        data = {}
        for object in objects:
            expenditure = object.expenditure
            amount = object.expenditure_amount
            if amount:
                data[expenditure] = data.get(expenditure, 0) + amount
        fig = px.pie(values=data.values(), names=data.keys(), title='支出构成')
        fig = fig.to_html(full_html=False)
        context = {'flag': 1, 'fig': fig}
        return render(request, 'IESys_/expenditure_detail.html', context)
    else:
        context = {'flag': 0}
        return render(request, 'IESys_/expenditure_detail.html', context)