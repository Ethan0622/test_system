from django.db.models import fields
from numpy import true_divide
from rest_framework import serializers
from users.models import MyUser
from .models import TestInfo, InitTestProcess, ObjectTestProcess
from itembank.models import TestItems


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


class ItemsPartSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.IntegerField(read_only=True)
    content = serializers.CharField(read_only=True)
    option_A = serializers.CharField(read_only=True)
    option_B = serializers.CharField(read_only=True)
    option_C = serializers.CharField(read_only=True)
    option_D = serializers.CharField(read_only=True)


class ItemInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.IntegerField(read_only=True)
    knowledge_id = serializers.PrimaryKeyRelatedField(read_only=True)
    discrimination = serializers.FloatField(read_only=True)
    difficulty = serializers.FloatField(read_only=True)
    guessing = serializers.FloatField(read_only=True)
