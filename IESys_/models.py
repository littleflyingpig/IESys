from django.db import models
from django.core.validators import MinValueValidator
# Create your models here.

class IeSys(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    income = models.CharField(max_length=50, null=True, blank=True)
    expenditure = models.CharField(max_length=50, null=True, blank=True)
    income_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, validators=[MinValueValidator(0, '收入不能为负数')])
    expenditure_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True,  validators=[MinValueValidator(0, '支出不能为负数')])
    def __str__(self):
        return f"{self.date}"