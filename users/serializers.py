from cProfile import label
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import MyUser
from testing.models import TestInfo


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['id', 'number', 'password', 'realname', 'type', 'email', 'joined_class']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        if validated_data.get('type') == 1:
            new_user = MyUser.objects.create_superuser(**validated_data)
        else:
            new_user = MyUser.objects.create_user(**validated_data)
        return new_user

    # 可修改字段：密码；真实姓名；邮箱
    def update(self, instance, validated_data):
        if ('password' in validated_data):
            instance.password = make_password(validated_data.get('password'))
        else:
            instance.password = instance.password
        instance.realname = validated_data.get('realname') or instance.realname
        instance.email = validated_data.get('email') or instance.email
        instance.save()
        return instance


class TestsListSerializer(serializers.Serializer):
    test_id = serializers.IntegerField(label='考试记录id', read_only=True)
    start_time = serializers.DateTimeField(label='考试开始时间', read_only=True)
    end_time = serializers.DateTimeField(label='考试结束时间', read_only=True)
    total_time = serializers.DurationField(label='考试总用时', read_only=True)
    final_ability = serializers.CharField(label='考试最终能力估计值', read_only=True)
