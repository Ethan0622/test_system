from django.shortcuts import render
from django.contrib.auth.hashers import make_password

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes

from .models import MyClass
from .serializers import ClassListSerializer
from users.serializers import UserSerializer
from users.utils import decode_token
from users.models import MyUser
from .utils import generate_invitation_code


class classListView(APIView):
    permission_classes = (IsAdminUser, )

    # 获取创建的所有班级
    def get(self, req):
        user_id = decode_token(req)['user_id']
        allClass = MyClass.objects.filter(teacher_id=user_id)
        classes = ClassListSerializer(allClass, many=True)
        return Response(classes.data, status.HTTP_200_OK)

    # 创建班级
    def post(self, req):
        postData = {}
        user_id = decode_token(req)['user_id']
        invitation_code = generate_invitation_code()
        postData['teacher_id'] = user_id
        postData['class_name'] = req.data['class_name']
        postData['invitation_code'] = invitation_code
        createClass = ClassListSerializer(data=postData)
        if createClass.is_valid(raise_exception=True):
            createClass.save()
            return Response(createClass.data, status.HTTP_201_CREATED)
        return Response(createClass.errors, status.HTTP_400_BAD_REQUEST)


class classInfoView(APIView):
    # 学生获取自己加入的班级
    def get(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        classId = None
        if user.type == 0 and user.joined_class:
            classId = user.joined_class.id
        else:
            return Response({}, status.HTTP_404_NOT_FOUND)
        theclass = MyClass.objects.get(id=classId)
        classInfo = ClassListSerializer(theclass)
        return Response(classInfo.data, status.HTTP_200_OK)

    # 学生加入班级
    def post(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        if user.type != 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        invitation_code = req.data['invitation_code']
        try:
            theclass = MyClass.objects.get(invitation_code=invitation_code)
        except MyClass.DoesNotExist:
            return Response({'msg': '邀请码有误'}, status.HTTP_404_NOT_FOUND)
        user.joined_class = theclass
        user.save()
        return Response({'msg': '加入班级成功'}, status.HTTP_200_OK)

    # 学生自己退出班级
    def delete(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        if user.type == 0:
            user.joined_class = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# 单个班级中针对学生相关的操作路由
class classStudentView(APIView):
    permission_classes = (IsAdminUser, )

    # 教师获取班级的所有学生
    def get(self, req, pk):
        try:
            theclass = MyClass.objects.get(id=pk)
        except MyClass.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        allStudent = MyUser.objects.filter(joined_class=theclass)
        students = UserSerializer(allStudent, many=True)
        return Response(students.data, status.HTTP_200_OK)

    # 教师重置某个学生的密码
    def put(self, req, pk):
        student_id = req.data.get('student_id')
        rePassword = req.data.get('repassword')
        if student_id and rePassword:
            try:
                thestudent = MyUser.objects.get(id=student_id)
            except MyUser.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if thestudent.joined_class and thestudent.joined_class.id == pk:
                thestudent.password = make_password(rePassword)
                thestudent.save()
                return Response({'msg': '重置成功'}, status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    # 教师将某个学生提出班级
    def delete(self, req, pk):
        student_id = req.data['student_id']
        student = MyUser.objects.get(id=student_id)
        if student.type == 0 and student.joined_class.id == pk:
            student.joined_class = None
            student.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# 单个班级的操作路由
class classDetailView(APIView):
    permission_classes = (IsAdminUser, )

    # 教师解散一个班级
    def delete(self, req, pk):
        try:
            theclass = MyClass.objects.get(id=pk)
        except MyClass.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        theclass.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)