from rest_framework import serializers
from .models import TestInfo, InitTestProcess, ObjectTestProcess
from itembank.models import TestItems


class TestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        fields = "__all__"


class ObjTestProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectTestProcess
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
    discrimination = serializers.FloatField(read_only=True)
    diffculty = serializers.FloatField(read_only=True)
    guessing = serializers.FloatField(read_only=True)
