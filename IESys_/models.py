from django.db import models

# Create your models here.

class IeSys(models.Model):
    date = models.DateField(auto_now_add=True)
    income = models.CharField(max_length=50, null=True, blank=True)
    expenditure = models.CharField(max_length=50, null=True, blank=True)
    income_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    expenditure_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    def __str__(self):
        return f"{self.date}"