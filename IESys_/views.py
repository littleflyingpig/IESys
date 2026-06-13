from django.shortcuts import render, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from .form import IeSysForm
from .models import IeSys


from collections import defaultdict
from datetime import date, timedelta, datetime
import time
import pandas as pd
import plotly.express as px
# Create your views here.

# ---------------------------------------------------------------------------
# 图表缓存工具
# ---------------------------------------------------------------------------

def _chart_cache_key(user_id, view_name, date_slug):
    """生成图表缓存键。版本号不存在时默认为 0。"""
    version = cache.get(f'chart_v:{user_id}', 0)
    return f'chart:{view_name}:{user_id}:v{version}:{date_slug}'

def bump_chart_cache(user_id):
    """用户新增/修改数据后调用，使该用户所有图表缓存失效。

    用时间戳作为新版本号，避免 incr 在多后端下的可靠性问题。
    """
    cache.set(f'chart_v:{user_id}', int(time.time()), timeout=None)

CACHE_TIMEOUT = 86400  # 24 小时（兜底，正常会被版本号自然淘汰）

def get_day_range(target_date):
    """获取某一天的开始和结束时间"""
    start = timezone.make_aware(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0))
    end = timezone.make_aware(datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59))
    return start, end

def index(request):
    """编写收支系统的主页视图"""
    context = {}
    if request.user.is_authenticated:
        today = timezone.localtime(timezone.now()).date()
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
            bump_chart_cache(request.user.id)
            return redirect('IESys_:index')
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
            bump_chart_cache(request.user.id)
            return redirect('IESys_:index')
    context = {'form': form}
    return render(request, 'IESys_/expenditure.html', context)

@never_cache
@login_required
def income_detail(request):
    """编写收入的详细页面视图"""
    today = timezone.localtime(timezone.now()).date()
    date_slug = today.isoformat()
    cache_key = _chart_cache_key(request.user.id, 'income_detail', date_slug)
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'IESys_/income_detail.html', cached)
    start, end = get_day_range(today)
    objects = IeSys.objects.filter(user=request.user, income_amount__gt=0, date__gte=start, date__lte=end)
    if objects:
        data = {}
        ic = []
        ac = []
        tc = []
        total_amount = 0
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
            total_amount += amount

        emerald_palette = [
            '#059669', '#10b981', '#34d399', '#6ee7b7',
            '#a7f3d0', '#047857', '#065f46', '#064e3b',
        ]

        fig = px.pie(
            values=list(data.values()),
            names=list(data.keys()),
            hole=0.45,
            color_discrete_sequence=emerald_palette,
        )

        fig.update_traces(
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=13, family='Microsoft YaHei, sans-serif', color='#475569'),
            hovertemplate=(
                '<b style="font-size:15px">%{label}</b><br>'
                '金额: <b>¥ %{value:.2f}</b><br>'
                '占比: <b>%{percent:.1%}</b>'
                '<extra></extra>'
            ),
            hoverlabel=dict(
                bgcolor='#ffffff',
                bordercolor='#10b981',
                font=dict(size=15, family='Microsoft YaHei, sans-serif', color='#1e293b'),
                align='left',
                namelength=-1,
            ),
            marker=dict(
                line=dict(color='#ffffff', width=2.5)
            ),
            pull=[0.03] * len(data),
            rotation=90,
            sort=False,
        )

        fig.update_layout(
            dragmode=False,
            hovermode='closest',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            autosize=True,
            margin=dict(t=70, l=20, r=20, b=30),
            title=dict(
                text='今日收入构成',
                font=dict(size=22, family='Microsoft YaHei, sans-serif', color='#1e293b'),
                x=0.5, xanchor='center',
                y=0.98,
            ),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom', y=-0.18,
                xanchor='center', x=0.5,
                font=dict(size=12, family='Microsoft YaHei, sans-serif', color='#64748b'),
                itemclick=False,
                itemdoubleclick=False,
            ),
            uniformtext=dict(minsize=11, mode='hide'),
        )

        fig_html = fig.to_html(
            full_html=False,
            config={
                'staticPlot': False,
                'scrollZoom': False,
                'displayModeBar': False,
                'responsive': True,
                'doubleClick': False,
                'showTips': False,
                'displaylogo': False,
            },
            include_plotlyjs='cdn'
        )
        
        combined = list(zip(ic, ac, tc))
        context = {'flag': 1, 'fig': fig_html, 'combined': combined, 'total_amount': total_amount}
        cache.set(cache_key, context, CACHE_TIMEOUT)
        return render(request, 'IESys_/income_detail.html', context)
    else:
        context = {'flag': 0}
        cache.set(cache_key, context, CACHE_TIMEOUT)
        return render(request, 'IESys_/income_detail.html', context)

@never_cache
@login_required
def expenditure_detail(request):
    """"编写支出的详细页面视图"""
    today = timezone.localtime(timezone.now()).date()
    date_slug = today.isoformat()
    cache_key = _chart_cache_key(request.user.id, 'expenditure_detail', date_slug)
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'IESys_/expenditure_detail.html', cached)
    start, end = get_day_range(today)
    objects = IeSys.objects.filter(user=request.user, expenditure_amount__gt=0, date__gte=start, date__lte=end)
    if objects:
        data = {}
        ed = []
        ad = []
        td = []
        total_amount = 0
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
            total_amount += amount

        red_palette = [
            '#dc2626', '#ef4444', '#f87171', '#fca5a5',
            '#fecaca', '#b91c1c', '#991b1b', '#7f1d1d',
        ]

        fig = px.pie(
            values=list(data.values()),
            names=list(data.keys()),
            hole=0.45,
            color_discrete_sequence=red_palette,
        )

        fig.update_traces(
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=13, family='Microsoft YaHei, sans-serif', color='#475569'),
            hovertemplate=(
                '<b style="font-size:15px">%{label}</b><br>'
                '金额: <b>¥ %{value:.2f}</b><br>'
                '占比: <b>%{percent:.1%}</b>'
                '<extra></extra>'
            ),
            hoverlabel=dict(
                bgcolor='#ffffff',
                bordercolor='#ef4444',
                font=dict(size=15, family='Microsoft YaHei, sans-serif', color='#1e293b'),
                align='left',
                namelength=-1,
            ),
            marker=dict(
                line=dict(color='#ffffff', width=2.5)
            ),
            pull=[0.03] * len(data),
            rotation=90,
            sort=False,
        )

        fig.update_layout(
            dragmode=False,
            hovermode='closest',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            autosize=True,
            margin=dict(t=70, l=20, r=20, b=30),
            title=dict(
                text='今日支出构成',
                font=dict(size=22, family='Microsoft YaHei, sans-serif', color='#1e293b'),
                x=0.5, xanchor='center',
                y=0.98,
            ),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom', y=-0.18,
                xanchor='center', x=0.5,
                font=dict(size=12, family='Microsoft YaHei, sans-serif', color='#64748b'),
                itemclick=False,
                itemdoubleclick=False,
            ),
            uniformtext=dict(minsize=11, mode='hide'),
        )

        fig_html = fig.to_html(
            full_html=False,
            config={
                'staticPlot': False,
                'scrollZoom': False,
                'displayModeBar': False,
                'responsive': True,
                'doubleClick': False,
                'showTips': False,
                'displaylogo': False,
            },
            include_plotlyjs='cdn'
        )
        
        combined = list(zip(ed, ad, td))
        context = {'flag': 1, 'fig': fig_html, 'combined': combined, 'total_amount': total_amount}
        cache.set(cache_key, context, CACHE_TIMEOUT)
        return render(request, 'IESys_/expenditure_detail.html', context)
    else:
        context = {'flag': 0}
        cache.set(cache_key, context, CACHE_TIMEOUT)
        return render(request, 'IESys_/expenditure_detail.html', context)

@never_cache
@login_required
def week_expenditure(request):
    """编写统计页面中的周统计"""
    today = timezone.localtime(timezone.now()).date()
    date_slug = today.isoformat()
    cache_key = _chart_cache_key(request.user.id, 'week', date_slug)
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'IESys_/week_expenditure.html', cached)
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

    week_start, week_end = get_day_range(monday)
    # 周日结束也用 get_day_range，保证范围正确
    _, week_end = get_day_range(sunday)

    # 一次查询整周数据
    week_records = IeSys.objects.filter(
        user=request.user, date__gte=week_start, date__lte=week_end
    )

    # 按天聚合
    daily_totals = [0] * 7
    for obj in week_records:
        local_date = timezone.localtime(obj.date).date()
        idx = (local_date - monday).days
        if 0 <= idx < 7:
            daily_totals[idx] += obj.expenditure_amount or 0

    amounts = daily_totals
    dates = [(monday + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    # 标记今天
    today_idx = today.weekday()
    bar_colors = ['#f87171' if i == today_idx else '#fca5a5' for i in range(7)]

    df = pd.DataFrame({
        '星期': week_labels,
        '日期': dates,
        '支出': amounts,
    })

    fig = px.bar(df, x='星期', y='支出',
                 hover_data={'日期': True, '星期': False},
                 color_discrete_sequence=['#f87171'])

    fig.update_traces(
        marker=dict(
            color=bar_colors,
            line=dict(color='#dc2626', width=1.2),
        ),
        hovertemplate=(
            '<b style="font-size:15px">%{customdata[0]}  %{x}</b><br>'
            '支出: <b>¥ %{y:.2f}</b>'
            '<extra></extra>'
        ),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#ef4444',
            font=dict(size=15, family='Microsoft YaHei, sans-serif', color='#1e293b'),
            align='left',
            namelength=-1,
        ),
        text=amounts,
        texttemplate='%{text:.2f}',
        textposition='outside',
        textfont=dict(size=12, family='Microsoft YaHei, sans-serif', color='#64748b'),
        width=0.6,
    )

    fig.update_xaxes(
        title=None,
        fixedrange=True,
        tickfont=dict(size=13, family='Microsoft YaHei, sans-serif', color='#475569'),
        gridcolor='rgba(0,0,0,0)',
    )
    fig.update_yaxes(
        title=dict(text='支出 (元)', font=dict(size=13, family='Microsoft YaHei, sans-serif', color='#94a3b8')),
        fixedrange=True,
        tickfont=dict(size=12, family='Microsoft YaHei, sans-serif', color='#94a3b8'),
        gridcolor='#f1f5f9',
        griddash='dot',
        zeroline=True,
        zerolinecolor='#e2e8f0',
    )

    fig.update_layout(
        dragmode=False,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        autosize=True,
        margin=dict(t=70, l=10, r=20, b=30),
        title=dict(
            text='本周支出统计',
            font=dict(size=22, family='Microsoft YaHei, sans-serif', color='#1e293b'),
            x=0.5, xanchor='center',
        ),
        showlegend=False,
        bargap=0.35,
    )

    fig_html = fig.to_html(
        full_html=False,
        config={
            'staticPlot': False,
            'scrollZoom': False,
            'displayModeBar': False,
            'responsive': True,
            'doubleClick': False,
            'showTips': False,
            'displaylogo': False,
        },
        include_plotlyjs='cdn'
    )

    context = {'fig': fig_html}
    cache.set(cache_key, context, CACHE_TIMEOUT)
    return render(request, 'IESys_/week_expenditure.html', context)

@never_cache
@login_required
def month_ie(request):
    """编写统计页面中的月收支"""
    today = timezone.localtime(timezone.now()).date()
    date_slug = today.isoformat()
    cache_key = _chart_cache_key(request.user.id, 'month', date_slug)
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'IESys_/month_ie.html', cached)
    cnt_day = today.day
    first_day = date(today.year, today.month, 1)

    days = []
    amounts = []

    # 一次查询整月数据（1号到今天）
    month_start, _ = get_day_range(first_day)
    _, today_end = get_day_range(today)
    month_records = IeSys.objects.filter(
        user=request.user, date__gte=month_start, date__lte=today_end
    )

    # 按天聚合当日净额
    daily_net_map = defaultdict(lambda: 0)
    for obj in month_records:
        local_date = timezone.localtime(obj.date).date()
        day_idx = local_date.day
        daily_net_map[day_idx] += (obj.income_amount or 0) - (obj.expenditure_amount or 0)

    cumulative = 0
    for i in range(1, cnt_day + 1):
        days.append(str(i))
        cumulative += daily_net_map.get(i, 0)
        amounts.append(cumulative)

    # 根据正负着色
    bar_colors = ['#10b981' if v >= 0 else '#ef4444' for v in amounts]
    # 最后一天(今天)用更深色高亮
    if bar_colors:
        last_color = '#059669' if amounts[-1] >= 0 else '#dc2626'
        bar_colors[-1] = last_color

    df = pd.DataFrame({
        '日': days,
        '累计结余': amounts,
    })

    fig = px.bar(df, x='日', y='累计结余')

    fig.update_traces(
        marker=dict(
            color=bar_colors,
            line=dict(color=['#047857' if v >= 0 else '#b91c1c' for v in amounts], width=1.2),
        ),
        hovertemplate=(
            '<b style="font-size:15px">%{x}日</b><br>'
            '累计结余: <b>¥ %{y:+,.2f}</b>'
            '<extra></extra>'
        ),
        hoverlabel=dict(
            bgcolor='#ffffff',
            bordercolor='#64748b',
            font=dict(size=15, family='Microsoft YaHei, sans-serif', color='#1e293b'),
            align='left',
            namelength=-1,
        ),
        text=amounts,
        texttemplate='%{text:+,.2f}',
        textposition='outside',
        textfont=dict(size=11, family='Microsoft YaHei, sans-serif', color='#64748b'),
        width=0.65,
    )

    fig.update_xaxes(
        title=dict(text=f'{today.month}月', font=dict(size=13, family='Microsoft YaHei, sans-serif', color='#94a3b8')),
        fixedrange=True,
        tickfont=dict(size=12, family='Microsoft YaHei, sans-serif', color='#475569'),
        gridcolor='rgba(0,0,0,0)',
    )
    fig.update_yaxes(
        title=dict(text='结余 (元)', font=dict(size=13, family='Microsoft YaHei, sans-serif', color='#94a3b8')),
        fixedrange=True,
        tickfont=dict(size=12, family='Microsoft YaHei, sans-serif', color='#94a3b8'),
        gridcolor='#f1f5f9',
        griddash='dot',
        zeroline=True,
        zerolinecolor='#e2e8f0',
    )

    fig.add_hline(y=0, line_dash='dash', line_color='#94a3b8', opacity=0.6)

    fig.update_layout(
        dragmode=False,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        autosize=True,
        margin=dict(t=70, l=10, r=20, b=30),
        title=dict(
            text=f'{today.month}月累计结余',
            font=dict(size=22, family='Microsoft YaHei, sans-serif', color='#1e293b'),
            x=0.5, xanchor='center',
        ),
        showlegend=False,
        bargap=0.3,
    )

    fig_html = fig.to_html(
        full_html=False,
        config={
            'staticPlot': False,
            'scrollZoom': False,
            'displayModeBar': False,
            'responsive': True,
            'doubleClick': False,
            'showTips': False,
            'displaylogo': False,
        },
        include_plotlyjs='cdn'
    )

    context = {'fig': fig_html}
    cache.set(cache_key, context, CACHE_TIMEOUT)
    return render(request, 'IESys_/month_ie.html', context)

@never_cache
@login_required
def total_detail(request):
    """编写首页的详情页面"""
    date_slug = 'all'
    cache_key = _chart_cache_key(request.user.id, 'total_detail', date_slug)
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'IESys_/total_detail.html', cached)

    result = list(IeSys.objects.filter(user=request.user).annotate(oneday=TruncDate('date')).values('oneday').annotate(
        expenditure = Sum('expenditure_amount'),
        income = Sum('income_amount')
    ).order_by('-oneday'))

    context = {'result': result}
    cache.set(cache_key, context, CACHE_TIMEOUT)
    return render(request, 'IESys_/total_detail.html', context)