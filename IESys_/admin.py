from django.contrib import admin

# Register your models here.
# 定义完模型后注册我自己的模型
from .models import IeSys
admin.site.register(IeSys)