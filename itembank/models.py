from django.db import models
from django.db.models.deletion import CASCADE, DO_NOTHING
from django.core.validators import (MinValueValidator)


class KnowledgePoints(models.Model):
    # 所属教材哪一章（1-8）
    chapter = models.IntegerField(null=False)
    # 主要知识点是什么
    content = models.CharField(max_length=255, null=False)


class ItemType(models.Model):
    # 类型名称
    type_name = models.CharField(max_length=100, null=False)
    # 是否是主观题
    is_subject = models.BooleanField(null=False)
    # 题目总分值
    total_score = models.IntegerField(null=False, validators=[MinValueValidator(0)])


class TestItems(models.Model):
    # 题目类型
    type = models.ForeignKey(ItemType, on_delete=DO_NOTHING, null=False)
    # 对应知识点
    knowledge_id = models.ForeignKey(KnowledgePoints, on_delete=CASCADE, null=False)
    # 题干信息
    content = models.CharField(max_length=255, null=False, unique=True)
    # 参考答案
    correct = models.CharField(max_length=255, null=False)
    # 题目区分度
    discrimination = models.FloatField(null=False, default=1)
    # 题目难度系数
    difficulty = models.FloatField(null=False)
    # 题目猜测系数
    guessing = models.FloatField(null=False, default=0)
    # 曝光系数
    exposure = models.FloatField(null=False, default=0)

    # 若type==1，则必须有选项，题目A、B、C、D选项
    option_A = models.CharField(max_length=255, null=True)
    option_B = models.CharField(max_length=255, null=True)
    option_C = models.CharField(max_length=255, null=True)
    option_D = models.CharField(max_length=255, null=True)
