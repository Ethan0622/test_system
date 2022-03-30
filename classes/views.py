import xlrd
from django.shortcuts import render
from django.contrib.auth.hashers import make_password

from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .models import MyClass
from .serializers import ClassListSerializer
from users.serializers import UserSerializer
from testing.serializers import TestInfoPartSerializer, SbjTestProcessDetailSerializer, SbjTestProcessSerializer
from users.utils import decode_token
from users.models import MyUser
from testing.models import SubjectTestProcess, TestInfo
from .utils import generate_invitation_code


class classListView(APIView):
    permission_classes = (IsAdminUser, )

    @swagger_auto_schema(responses={200: ClassListSerializer},
                         operation_summary='教师获取创建的所有班级')
    def get(self, req):
        user_id = decode_token(req)['user_id']
        allClass = MyClass.objects.filter(teacher_id=user_id)
        classes = ClassListSerializer(allClass, many=True)
        return Response(classes.data, status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['class_name'],
        properties={
            'class_name': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             201: ClassListSerializer
                         },
                         operation_summary='教师创建一个新班级')
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
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: ClassListSerializer
    },
                         operation_summary='学生获取自己所在班级的信息')
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

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['invitation_code'],
        properties={
            'invitation_code': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             200: 'OK'
                         },
                         operation_summary='学生加入一个班级')
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

    @swagger_auto_schema(responses={
        204: 'No Content',
        400: 'Bad Request'
    },
                         operation_summary='学生主动退出自己的班级')
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

    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: UserSerializer
    },
                         operation_summary='教师获取一个班级里的所有学生信息')
    def get(self, req, pk):
        try:
            theclass = MyClass.objects.get(id=pk)
        except MyClass.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        allStudent = MyUser.objects.filter(joined_class=theclass)
        students = UserSerializer(allStudent, many=True)
        return Response(students.data, status.HTTP_200_OK)

    # 教师帮助学生创建账号并批量添加进入指定班级
    def post(self, req, pk):
        try:
            theclass = MyClass.objects.get(id=pk)
        except MyClass.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        uploadFile = req.FILES['file']
        wb = xlrd.open_workbook(filename=None, file_contents=uploadFile.read())
        table = wb.sheets()[0]
        rows = table.nrows
        cols = table.ncols
        if cols != 2:
            return Response({'errors': ['请使用本网站所提供的excel模板进行提交']},
                            status.HTTP_400_BAD_REQUEST)
        user_key = ['number', "realname", "type", 'password', "joined_class"]

        existUserList = []
        for i in range(1, rows):
            row = table.row_values(i)
            row[0] = int(row[0])
            if '' in row:
                return Response({'errors': ['部分学生的信息未填写，请检查']},
                                status.HTTP_400_BAD_REQUEST)
            row = row + [0, '123456', theclass.id]
            userInfo = dict(zip(user_key, row))
            createUser = UserSerializer(data=userInfo)
            if createUser.is_valid():
                createUser.save()
            else:
                existUserList.append(row[0])
        return Response({'warnings': existUserList}, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['student_id', 'repassword'],
        properties={
            'student_id': openapi.Schema(type=openapi.TYPE_NUMBER),
            'repassword': openapi.Schema(type=openapi.TYPE_STRING)
        },
    ),
                         responses={
                             400: 'Bad Request',
                             200: 'OK'
                         },
                         operation_summary='教师重置某个学生的密码')
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

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['student_id', 'repassword'],
        properties={'student_id': openapi.Schema(type=openapi.TYPE_NUMBER)},
    ),
                         responses={
                             400: 'Bad Request',
                             200: 'OK'
                         },
                         operation_summary='教师将某个学生踢出班级')
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
    # pk指某个班级id
    permission_classes = (IsAdminUser, )

    student_id = openapi.Parameter('student_id',
                                   required=True,
                                   in_=openapi.IN_QUERY,
                                   description='学生Id',
                                   type=openapi.TYPE_NUMBER)

    @swagger_auto_schema(manual_parameters=[student_id],
                         responses={
                             400: 'Bad Request',
                             200: TestInfoPartSerializer
                         },
                         operation_summary='教师获取班级中某个学生的全部考试信息')
    def get(self, req, pk):
        student_id = int(req.GET.get('student_id'))
        student = MyUser.objects.get(id=student_id)
        if student.type == 0 and student.joined_class.id == pk:
            all_tests_qs = TestInfo.objects.filter(user_id=student_id)
            now_time = datetime.now()
            for item in all_tests_qs:
                if (not item.end_time):
                    if (not item.total_time):
                        if ((now_time - item.start_time) > timedelta(hours=2)):
                            item.total_time = timedelta(hours=2)
                            item.save()

            all_tests_qs = TestInfo.objects.filter(user_id=student_id)
            all_test = TestInfoPartSerializer(all_tests_qs, many=True)
            return Response(all_test.data, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={
        400: 'Bad Request',
        204: 'No Content'
    },
                         operation_summary='教师解散一个班级')
    def delete(self, req, pk):
        try:
            theclass = MyClass.objects.get(id=pk)
        except MyClass.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        theclass.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class classTestView(APIView):
    # pk指考试信息id
    permission_classes = (IsAdminUser, )

    @swagger_auto_schema(responses={
        200: SbjTestProcessDetailSerializer,
    },
                         operation_summary='教师获取班级中一个学生的某次考试的主观题回答')
    def get(self, req, pk):
        sbj_test_process_qs = SubjectTestProcess.objects.filter(test_id=pk)
        sbj_test_process = SbjTestProcessDetailSerializer(sbj_test_process_qs, many=True)
        return Response(sbj_test_process.data, status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['subject_id', 'score'],
        properties={
            'subject_id': openapi.Schema(description='主观题回答记录id',
                                         type=openapi.TYPE_NUMBER),
            'score': openapi.Schema(type=openapi.TYPE_NUMBER)
        },
    ),
                         responses={
                             400: 'Bad Request',
                             200: SbjTestProcessSerializer
                         },
                         operation_summary='教师对主观题回答评分')
    def post(self, req, pk):
        sbjProcessId = req.data['subject_id']
        sbjProcess = SubjectTestProcess.objects.get(id=sbjProcessId)
        if sbjProcess.test_id.test_id == pk:
            saveSbjScore = SbjTestProcessSerializer(sbjProcess, req.data, partial=True)
            if saveSbjScore.is_valid(raise_exception=True):
                saveSbjScore.save()
                return Response(saveSbjScore.data, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
