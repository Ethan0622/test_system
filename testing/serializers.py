from rest_framework import serializers
from .models import TestInfo, InitTestProcess, ObjectTestProcess

class TestInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestInfo
        fields = "__all__"