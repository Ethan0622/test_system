from django.db import models
from django.db.models.deletion import CASCADE
from users.models import MyUser
from itembank.models import TestItems


# 学生开始一次考试即新增一条记录
class TestInfo(models.Model):
    test_id = models.AutoField(primary_key=True, unique=True, null=False)

    start_time = models.DateTimeField(verbose_name='考试开始时间', null=False)

    end_time = models.DateTimeField(verbose_name='考试结束时间', default=None, null=True)

    total_time = models.DurationField(verbose_name='总考试用时', null=True)

    newest_ability = models.FloatField(verbose_name='做题过程中最新的能力值评估', null=True)

    final_ability = models.CharField(verbose_name='最终能力估计', max_length=100, null=True)

    finish_object_test = models.BooleanField(verbose_name='是否完成客观题测试', null=True)

    user_id = models.ForeignKey(MyUser, on_delete=CASCADE)


# 若学生是第一次考试，还没有初始能力值的估计，则初始能力值估计的考试过程记录于此
class InitTestProcess(models.Model):
    test_id = models.ForeignKey(TestInfo, on_delete=CASCADE)

    item_id = models.ForeignKey(TestItems, on_delete=CASCADE)

    answer = models.CharField(verbose_name='学生的回答', max_length=255, null=False)

    judge = models.BooleanField(verbose_name='是否正确', null=False)


# 正式开始考试后的客观题做题过程
class ObjectTestProcess(models.Model):
    test_id = models.ForeignKey(TestInfo, on_delete=CASCADE)

    item_id = models.ForeignKey(TestItems, on_delete=CASCADE)

    answer = models.CharField(verbose_name='学生的回答', max_length=255, null=False)

    judge = models.BooleanField(verbose_name='是否正确', null=False)

    process_ability = models.FloatField(verbose_name='做完此题后的能力评估', null=False)


# 正式开始考试后的主观题做题过程
class SubjectTestProcess(models.Model):
    test_id = models.ForeignKey(TestInfo, on_delete=CASCADE)

    item_id = models.ForeignKey(TestItems, on_delete=CASCADE)

    # 由于主观题学生答案字数难以预估，故使用更大的数据库字段存放
    answer = models.TextField(verbose_name='学生的回答', null=False)

    # 教师给出或系统评价给出的评分，可以暂时为空
    score = models.FloatField(verbose_name='得分', null=True)
