from django.shortcuts import render, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.utils import timezone
from .form import IeSysForm
from .models import IeSys

from datetime import date, timedelta
import calendar
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
            form.save()
            messages.success(request, '支出添加成功！')
            return redirect('IESys_:income')
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
    
def week_expenditure(request):
    """编写统计页面中的周统计"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    amount = []
    while monday <= sunday:
        objects = IeSys.objects.filter(date=monday)
        if not objects:
            amount.append(0)
        else:
            total = 0
            for object in objects:
                total += object.expenditure_amount
            amount.append(total)
        monday += timedelta(days=1)
    df = pd.DataFrame({
        '本周': week,
        '支出': amount
    })
    fig = px.bar(df, x='本周', y='支出', title='周支出统计')
    fig = fig.to_html(full_html=False)
    context = {'fig': fig}
    return render(request, 'IESys_/week_expenditure.html', context)

def month_ie(request):
    """编写统计页面中的月收支"""
    today = date.today()
    total_days = calendar.monthrange(today.year, today.month)[1]
    first_day = date(today.year, today.month, 1)
    days = []
    amount = []
    for i in range(total_days):
        cnt = first_day + timedelta(days=i)
        
        days.append(str(cnt.day))
        objects = IeSys.objects.filter(date=cnt)
        if objects:
            total = 0
            for object in objects:
                total += object.income_amount - object.expenditure_amount
            if i == 0:
                amount.append(total)
            else:
                total += amount[i-1]
                amount.append(total)
        else:
            if i == 0:
                amount.append(0)
            else:
                amount.append(amount[i-1])
    data = pd.DataFrame({
        '日': days,
        '总收支': amount
    })
    fig = px.bar(data, x='日', y='总收支', title=str(today.month)+'月总收支统计')
    fig.update_xaxes(title_text=str(today.month)+'月')
    fig = fig.to_html(full_html=False)
    context = {'fig': fig}
    return render(request, 'IESys_/month_ie.html', context)
