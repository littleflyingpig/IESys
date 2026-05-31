from django.urls import path
from . import views
# IESys_的 url

app_name = 'IESys_'
urlpatterns = [
    path('', views.index, name='index'),
    path('ie/', views.ie, name='ie'),
    path('sta/', views.sta,  name='sta'),
    path('income', views.income, name='income'),
    path('expenditure', views.expenditure, name='expenditure'),
    path('income_detail/', views.income_detail, name='income_detail'),
    path('expenditure_detail/', views.expenditure_detail, name='expenditure_detail'),
]