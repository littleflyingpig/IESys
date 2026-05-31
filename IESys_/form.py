from django import forms
from .models import IeSys
#创建我的表单
class IeSysForm(forms.ModelForm):
    class Meta:
        model = IeSys
        fields = ['income', 'expenditure', 'income_amount', 'expenditure_amount']