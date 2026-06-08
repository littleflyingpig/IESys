from django.shortcuts import render, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate
from .form import IeSysForm
from .models import IeSys


from datetime import date, timedelta, datetime
import calendar
import pandas as pd
import plotly.express as px
# Create your views here.

def get_day_range(target_date):
    """获取某一天的开始和结束时间"""
    start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    return start, end


def index(request):
    """编写收支系统的主页视图"""
    context = {}
    if request.user.is_authenticated:
        today = timezone.now().date()
        start, end = get_day_range(today)

        # 今日收入
        today_income = IeSys.objects.filter(
            user=request.user, income_amount__gt=0,
            date__gte=start, date__lte=end
        ).aggregate(total=Sum('income_amount'))['total'] or 0

        # 今日支出
        today_expense = IeSys.objects.filter(
            user=request.user, expenditure_amount__gt=0,
            date__gte=start, date__lte=end
        ).aggregate(total=Sum('expenditure_amount'))['total'] or 0

        # 本月累计结余
        first_day = date(today.year, today.month, 1)
        month_income = IeSys.objects.filter(
            user=request.user, date__gte=first_day
        ).aggregate(total=Sum('income_amount'))['total'] or 0
        month_expense = IeSys.objects.filter(
            user=request.user, date__gte=first_day
        ).aggregate(total=Sum('expenditure_amount'))['total'] or 0

        context = {
            'today_income': today_income,
            'today_expense': today_expense,
            'month_balance': month_income - month_expense,
        }
    return render(request, 'IESys_/index.html', context)

@login_required
def ie(request):
    """编写主页中跳转收支页面的视图"""
    return render(request, 'IESys_/ie.html')

@login_required
def sta(request):
    """编写主页中统计页面的视图"""
    return render(request, 'IESys_/sta.html')

@login_required
def income(request):
    """编写收支页面的收入的视图"""
    if request.method != "POST":
        form = IeSysForm()
    else:
        form = IeSysForm(data=request.POST)
        if form.is_valid():
            form.instance.user = request.user
            form.save()
            messages.success(request, '收入添加成功！')
            return redirect('IESys_:income')
    context = {'form': form}
    return render(request, 'IESys_/income.html', context)

@login_required
def expenditure(request):
    """"编写支出页面的支出视图"""
    if request.method != "POST":
        form = IeSysForm()
    else:
        form = IeSysForm(data=request.POST)
        if form.is_valid():
            form.instance.user = request.user
            form.save()
            messages.success(request, "支出添加成功！")
            return redirect('IESys_:expenditure')
    context = {'form': form}
    return render(request, 'IESys_/expenditure.html', context)

@login_required
def income_detail(request):
    """编写收入的详细页面视图"""
    today = timezone.now().date()
    start, end = get_day_range(today)
    objects = IeSys.objects.filter(user=request.user, income_amount__gt=0, date__gte=start, date__lte=end)
    if objects:
        data = {}
        ic = []
        ac = []
        tc = []
        total_amount = 0  # 添加总金额变量
        for obj in objects:
            income = obj.income
            amount = obj.income_amount
            time = obj.date

            if not amount or amount == 0:
                continue

            ic.append(income)
            ac.append(amount)
            tc.append(time)
            data[income] = data.get(income, 0) + amount
            total_amount += amount  # 累加总金额
        
        fig = px.pie(values=list(data.values()), names=list(data.keys()), title='收入构成')
        fig = fig.to_html(full_html=False)
        combined = zip(ic, ac, tc)
        context = {'flag': 1, 'fig': fig, 'combined': combined, 'total_amount': total_amount}
        return render(request, 'IESys_/income_detail.html', context)
    else:
        context = {'flag': 0}
        return render(request, 'IESys_/income_detail.html', context)
    
@login_required
def expenditure_detail(request):
    """"编写支出的详细页面视图"""
    today = timezone.now().date()
    start, end = get_day_range(today)
    objects = IeSys.objects.filter(user=request.user, expenditure_amount__gt=0, date__gte=start, date__lte=end)
    if objects:
        data = {}
        ed = []
        ad = []
        td = []
        total_amount = 0  # 添加总金额变量
        for obj in objects:
            expenditure = obj.expenditure
            amount = obj.expenditure_amount
            time = obj.date

            if not amount or amount == 0:
                continue

            ed.append(expenditure)
            ad.append(amount)
            td.append(time)
            data[expenditure] = data.get(expenditure, 0) + amount
            total_amount += amount  # 累加总金额
        
        fig = px.pie(values=list(data.values()), names=list(data.keys()), title='支出构成')
        fig = fig.to_html(full_html=False)
        combined = zip(ed, ad, td)
        context = {'flag': 1, 'fig': fig, 'combined': combined, 'total_amount': total_amount}
        return render(request, 'IESys_/expenditure_detail.html', context)
    else:
        context = {'flag': 0}
        return render(request, 'IESys_/expenditure_detail.html', context)

@login_required
def week_expenditure(request):
    """编写统计页面中的周统计"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    amount = []
    
    current = monday
    while current <= sunday:
        start, end = get_day_range(current)
        objects = IeSys.objects.filter(user=request.user, date__gte=start, date__lte=end)
        
        total = 0
        for obj in objects:
            total += obj.expenditure_amount or 0
        amount.append(total)
        current += timedelta(days=1)
    
    df = pd.DataFrame({
        '本周': week,
        '支出': amount
    })
    fig = px.bar(df, x='本周', y='支出', title='周支出统计')
    fig = fig.to_html(full_html=False)
    context = {'fig': fig}
    return render(request, 'IESys_/week_expenditure.html', context)

@login_required
def month_ie(request):
    """编写统计页面中的月收支"""
    today = date.today()
    total_days = calendar.monthrange(today.year, today.month)[1]
    first_day = date(today.year, today.month, 1)

    # total_balance = IeSys.get_total_balance()

    total_income = IeSys.objects.filter(user=request.user).aggregate(total=Sum('income_amount'))['total'] or 0
    total_expense = IeSys.objects.filter(user=request.user).aggregate(total=Sum('expenditure_amount'))['total'] or 0
    total_balance = total_income - total_expense
    
    days = []
    amount = []
    cumulative = total_balance
    
    for i in range(total_days):
        current_date = first_day + timedelta(days=i)
        days.append(str(current_date.day))
        
        start, end = get_day_range(current_date)
        objects = IeSys.objects.filter(user=request.user, date__gte=start, date__lte=end)
        
        daily_net = 0
        for obj in objects:
            daily_net += (obj.income_amount or 0) - (obj.expenditure_amount or 0)
        
        cumulative += daily_net
        amount.append(cumulative)
    
    data = pd.DataFrame({
        '日': days,
        '总收支': amount
    })
    fig = px.bar(data, x='日', y='总收支', title=str(today.month)+'月总收支统计')
    fig.update_xaxes(title_text=str(today.month)+'月')
    fig = fig.to_html(full_html=False)
    context = {'fig': fig}
    return render(request, 'IESys_/month_ie.html', context)

@login_required
def total_detail(request):
    """编写首页的详情页面"""
    result = IeSys.objects.filter(user=request.user).annotate(oneday=TruncDate('date')).values('oneday').annotate(
        expenditure = Sum('expenditure_amount'),
        income = Sum('income_amount')
    ).order_by('-oneday')

    context = {'result': result}
    return render(request, 'IESys_/total_detail.html', context)