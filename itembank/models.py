from os import truncate
from django.db import models


class ChoiceItems(models.Model):
    # 题目类型，暂定选择题(1)、是非题(2)、论述题
    type = models.IntegerField(null=False)
    # 题干信息
    content = models.CharField(max_length=255, null=False, unique=True)
    # 题目A、B、C、D选项
    option_A = models.CharField(max_length=255, null=False)
    option_B = models.CharField(max_length=255, null=False)
    option_C = models.CharField(max_length=255, null=False)
    option_D = models.CharField(max_length=255, null=False)

    correct = models.CharField(max_length=30, null=False)
    # 题目区分度
    discrimination = models.FloatField(null=False)
    # 题目难度系数
    diffculty = models.FloatField(null=False)
    # 题目猜测系数
    guessing = models.FloatField(null=False)


class TFItems(models.Model):
    # 题目类型，是非题(2)
    type = models.IntegerField(null=False)
    content = models.CharField(max_length=255, null=False, unique=True)
    correct = models.BooleanField(null=False)
    # 题目区分度
    discrimination = models.FloatField(null=False)
    # 题目难度系数
    diffculty = models.FloatField(null=False)
    # 题目猜测系数
    guessing = models.FloatField(null=False)
