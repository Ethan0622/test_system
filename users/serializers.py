from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import MyUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['id', 'number', 'password', 'realname', 'type', 'email']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
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