from pyexpat import model
from rest_framework import serializers
from users.models import MyUser
from .models import TestInfo, InitTestProcess, ObjectTestProcess, SubjectTestProcess
from itembank.models import TestItems, ItemType


class TestInfoStartSer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        fields = ['test_id', 'start_time', 'newest_ability', 'user_id']
        read_only_fields = ['test_id']
        extra_kwargs = {'start_time': {'write_only': True}}


class TestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        fields = "__all__"


class TestInfoPartSerializer(serializers.ModelSerializer):
    un_grade = serializers.SerializerMethodField('is_un_grade_test')

    def is_un_grade_test(self, TestInfo):
        un_grade = False
        if (TestInfo.end_time and TestInfo.total_time):
            obj_answer_qs = SubjectTestProcess.objects.filter(test_id=TestInfo.test_id)
            for item in obj_answer_qs:
                if item.score == None:
                    un_grade = True
                    break
        return un_grade

    class Meta:
        model = TestInfo
        fields = [
            'test_id', 'start_time', 'end_time', 'total_time', 'final_ability', 'un_grade'
        ]


class TestInfoFinishSer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        fields = ['test_id', 'end_time', 'total_time', 'final_ability']
        read_only_fields = ['test_id']
        extra_kwargs = {'end_time': {'write_only': True}}


class ObjTestProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectTestProcess
        fields = "__all__"


class InitTestProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = InitTestProcess
        fields = "__all__"


class SbjTestProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectTestProcess
        fields = "__all__"


class SbjTestProcessDetailSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField('get_item_content')
    type = serializers.SerializerMethodField('get_item_type')

    def get_item_content(self, SubjectTestProcess):
        return TestItems.objects.get(id=SubjectTestProcess.item_id.id).content

    def get_item_type(self, SubjectTestProcess):
        return TestItems.objects.get(id=SubjectTestProcess.item_id.id).type.id

    class Meta:
        model = SubjectTestProcess
        fields = ['id', 'content', 'type', 'answer', 'item_id', 'score']


class ItemsPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestItems
        fields = ['id', 'type', 'content', 'option_A', 'option_B', 'option_C', 'option_D']
        read_only_fields = [
            'id', 'type', 'content', 'option_A', 'option_B', 'option_C', 'option_D'
        ]

    # id = serializers.IntegerField(read_only=True)
    # type = serializers.PrimaryKeyRelatedField(read_only=True)
    # content = serializers.CharField(read_only=True)
    # option_A = serializers.CharField(read_only=True)
    # option_B = serializers.CharField(read_only=True)
    # option_C = serializers.CharField(read_only=True)
    # option_D = serializers.CharField(read_only=True)


class ItemInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestItems
        fields = [
            'id', 'type', 'knowledge_id', 'discrimination', 'difficulty', 'guessing',
            'exposure'
        ]
        read_only_fields = [
            'id', 'type', 'knowledge_id', 'discrimination', 'difficulty', 'guessing',
            'exposure'
        ]

    # id = serializers.IntegerField(read_only=True)
    # type = serializers.PrimaryKeyRelatedField(read_only=True)
    # knowledge_id = serializers.PrimaryKeyRelatedField(read_only=True)
    # discrimination = serializers.FloatField(read_only=True)
    # difficulty = serializers.FloatField(read_only=True)
    # guessing = serializers.FloatField(read_only=True)
    # exposure = serializers.FloatField(read_only=True)


class ObjectResultSerializer(serializers.ModelSerializer):
    item_content = serializers.CharField(source='item_id.content', read_only=True)
    # item_correct = serializers.CharField(source='item_id.correct', read_only=True)
    item_correct = serializers.SerializerMethodField('get_item_correct')
    answer_content = serializers.SerializerMethodField('get_option')

    def get_item_correct(self, ObjectTestProcess):
        item = TestItems.objects.get(id=ObjectTestProcess.item_id.id)
        if (item.type.id == 1):
            switch = {
                'A': item.option_A,
                'B': item.option_B,
                'C': item.option_C,
                'D': item.option_D
            }
            try:
                correctContent = switch[item.correct]
                return item.correct + '、' + correctContent
            except KeyError as e:
                return item.correct
        else:
            return TestItems.objects.get(id=ObjectTestProcess.item_id.id).correct

    def get_option(self, ObjectTestProcess):
        item = TestItems.objects.get(id=ObjectTestProcess.item_id.id)
        if (item.type.id == 1):
            switch = {
                'A': item.option_A,
                'B': item.option_B,
                'C': item.option_C,
                'D': item.option_D
            }
            try:
                answerContent = switch[ObjectTestProcess.answer]
                return ObjectTestProcess.answer + '、' + answerContent
            except KeyError as e:
                return ObjectTestProcess.answer
        else:
            return ObjectTestProcess.answer

    class Meta:
        model = ObjectTestProcess
        fields = [
            'item_id', 'answer', 'judge', 'item_content', 'item_correct', 'answer_content'
        ]


class SubjectResultSerializer(serializers.ModelSerializer):
    item_content = serializers.CharField(source='item_id.content', read_only=True)
    item_correct = serializers.CharField(source='item_id.correct', read_only=True)

    class Meta:
        model = SubjectTestProcess
        fields = ['item_id', 'answer', 'score', 'item_content', 'item_correct']