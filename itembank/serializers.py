from rest_framework import serializers
from .models import TestItems, ItemType, TestPaperInfo, TestPaper


class ItemsAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestItems
        fields = "__all__"

    def validate(self, value):
        keys = ["option_A", "option_B", "option_C", "option_D"]
        type = value.get('type')
        if type and type == 1:
            for item in keys:
                if value.get(item) == None:
                    message = '请补充完善选择题的选项'
                    raise serializers.ValidationError(message)
            return value
        else:
            return value


class ItemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemType
        fields = "__all__"


class TestPaperInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestPaperInfo
        fields = "__all__"


class TestPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestPaper
        fields = "__all__"