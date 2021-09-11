from django.db import models
from django.db.models.deletion import CASCADE
from users.models import MyUser

class TestInfo(models.Model):
    test_id = models.AutoField(primary_key=True, unique=True, null=False)

    start_time = models.TimeField(verbose_name='考试开始时间', auto_now_add=True, null=False)

    end_time = models.TimeField(verbose_name='考试结束时间', auto_now=True, null=True)

    total_time = models.DurationField(verbose_name='总考试用时', null=True)

    newest_ability = models.FloatField(verbose_name='做题过程中最新的能力值评估', null=True)

    final_ability = models.CharField(verbose_name='最终能力估计', null=True)

    user_id = models.ForeignKey(MyUser, on_delete=CASCADE)


# class TestProcess(models.Model):
    
