from django.db import models
from django.db.models.deletion import CASCADE, DO_NOTHING
from django.core.validators import (MinValueValidator)
from users.models import MyUser


class KnowledgePoints(models.Model):
    # 所属教材哪一章（1-8）
    chapter = models.IntegerField(verbose_name='对应教材章节', null=False)
    # 主要知识点是什么
    content = models.CharField(verbose_name='对应教材内容', max_length=255, null=False)


class ItemType(models.Model):
    # 类型名称
    type_name = models.CharField(verbose_name='题型', max_length=100, null=False)
    # 是否是主观题
    is_subject = models.BooleanField(verbose_name='是否为主观题', null=False)
    # 题目总分值
    total_score = models.IntegerField(verbose_name='分值',
                                      null=False,
                                      validators=[MinValueValidator(0)])


class TestItems(models.Model):
    # 题目类型
    type = models.ForeignKey(ItemType, on_delete=DO_NOTHING, null=False)
    # 对应知识点
    knowledge_id = models.ForeignKey(KnowledgePoints, on_delete=CASCADE, null=False)
    # 题干信息
    content = models.TextField(verbose_name='题干', null=False)  # 暂时去掉唯一性，优先保证长度够
    # 参考答案
    correct = models.TextField(verbose_name='参考答案', null=False)
    # 题目区分度
    discrimination = models.FloatField(verbose_name='区分度系数', null=False, default=1)
    # 题目难度系数
    difficulty = models.FloatField(verbose_name='难度系数', null=False)
    # 题目猜测系数
    guessing = models.FloatField(verbose_name='猜测系数', null=False, default=0)
    # 曝光系数
    exposure = models.FloatField(verbose_name='曝光系数', null=False, default=0)

    # 若type==1，则必须有选项，题目A、B、C、D选项
    option_A = models.TextField(verbose_name='选项A', null=True)
    option_B = models.TextField(verbose_name='选项B', null=True)
    option_C = models.TextField(verbose_name='选项C', null=True)
    option_D = models.TextField(verbose_name='选项D', null=True)


class ItemImages(models.Model):
    item_id = models.ForeignKey(TestItems,
                                related_name='item_images',
                                on_delete=CASCADE,
                                null=False)
    img_site = models.IntegerField(verbose_name='此图片用在题目的什么位置.默认：1=题干中；特殊：2=选择题的选项中',
                                   default=1)
    img_url = models.ImageField(upload_to='images/')


class TestPaperInfo(models.Model):
    # 试题名称
    paper_name = models.CharField(max_length=100, null=False)
    # 创建时间
    paper_ctime = models.DateField(auto_now_add=True)
    # 创建教师
    paper_teacher = models.ForeignKey(MyUser, on_delete=DO_NOTHING, null=False)


class TestPaper(models.Model):
    # 对应试卷id
    paper_id = models.ForeignKey(TestPaperInfo, on_delete=CASCADE, null=False)
    # 相应题目id
    item_id = models.ForeignKey(TestItems, on_delete=CASCADE, null=False)