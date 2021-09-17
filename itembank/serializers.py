from rest_framework import serializers
from .models import TestItems


class itemsPartSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.IntegerField(required=True)
    content = serializers.CharField(max_length=255, required=True)
    option_A = serializers.CharField(max_length=255)
    option_B = serializers.CharField(max_length=255)
    option_C = serializers.CharField(max_length=255)
    option_D = serializers.CharField(max_length=255)


class itemsAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestItems
        fields = "__all__"