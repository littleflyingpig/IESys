from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Sum
from django.contrib.auth.models import User
# Create your models here.

class IeSys(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    income = models.CharField(max_length=50, null=True, blank=True)
    expenditure = models.CharField(max_length=50, null=True, blank=True)
    income_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0, '收入不能为负数')])
    expenditure_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,  validators=[MinValueValidator(0, '支出不能为负数')])
    def __str__(self):
        return f"{self.date}"
    
    # @classmethod
    # def get_total_balance(cls):
    #     """计算所有记录的总余额"""
    #     total_income = cls.objects.aggregate(total=Sum('income_amount'))['total'] or 0
    #     total_expense = cls.objects.aggregate(total=Sum('expenditure_amount'))['total'] or 0
    #     return total_income - total_expense