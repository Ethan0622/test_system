from numpy import source
from rest_framework import serializers
from .models import MyClass
from users.models import MyUser


class ClassListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher_id.realname', read_only=True)

    class Meta:
        model = MyClass
        fields = [
            'id', 'class_name', 'create_time', 'invitation_code', 'teacher_id',
            'teacher_name'
        ]
        # read_only_fields = ['id', 'teacher_name']
        read_only_fields = ('id', )
