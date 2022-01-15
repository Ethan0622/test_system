from typing import Callable
from django.db import models
from django.db.models.deletion import CASCADE


class KnowledgePoints(models.Model):
    # 所属教材哪一章（1-8）
    chapter = models.IntegerField(null=False)
    # 主要知识点是什么
    content = models.CharField(max_length=255, null=False)


class TestItems(models.Model):
    # 题目类型，暂定选择题(1)、判断题(2)、简答题(3)
    type = models.IntegerField(null=False)
    # 对应知识点
    knowledge_id = models.ForeignKey(KnowledgePoints, on_delete=CASCADE, default=1)
    # 题干信息
    content = models.CharField(max_length=255, null=False, unique=True)
    # 参考答案
    correct = models.CharField(max_length=255, null=False)
    # 题目区分度
    discrimination = models.FloatField(null=False)
    # 题目难度系数
    difficulty = models.FloatField(null=False)
    # 题目猜测系数
    guessing = models.FloatField(null=False)

    # 若type==1，则必须有选项，题目A、B、C、D选项
    option_A = models.CharField(max_length=255, null=True)
    option_B = models.CharField(max_length=255, null=True)
    option_C = models.CharField(max_length=255, null=True)
    option_D = models.CharField(max_length=255, null=True)
