from rest_framework import serializers
from .models import ChoiceItems, TFItems


class choicePartSerializer(serializers.Serializer):
    type = serializers.IntegerField(required=True)
    content = serializers.CharField(max_length=255, required=True)
    option_A = serializers.CharField(max_length=255, required=True)
    option_B = serializers.CharField(max_length=255, required=True)
    option_C = serializers.CharField(max_length=255, required=True)
    option_D = serializers.CharField(max_length=255, required=True)


class choiceAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceItems
        fields = "__all__"


class TFPartSerializer(serializers.Serializer):
    type = serializers.IntegerField(required=True)
    content = serializers.CharField(max_length=255, required=True)


class TFAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = TFItems
        fields = "__all__"