from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework_jwt.settings import api_settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .models import MyUser
from testing.models import TestInfo
from .serializers import UserSerializer, TestsListSerializer
from testing.serializers import TestInfoFinishSer, TestInfoSerializer
from .utils import decode_token

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
jwt_response_payload_handler = api_settings.JWT_RESPONSE_PAYLOAD_HANDLER


class userLoginJWTView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['number', 'password'],
        properties={
            'number': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             404: 'Not found',
                             200: UserSerializer
                         },
                         security=[],
                         operation_summary='用户登录')
    def post(self, request, *args, **kwargs):
        number = request.data.get('number')
        password = request.data.get('password')
        try:
            # 手动通过 user 签发 jwt-token
            user = MyUser.objects.get(number=number)
        except:
            return Response({'msg': '用户未注册'}, status=status.HTTP_404_NOT_FOUND)
        # 获得用户后，校验密码并签发token
        if not user.check_password(password):
            return Response({'msg': '密码错误'}, status=status.HTTP_400_BAD_REQUEST)
        '''
        检测用户测试情况，如果有测验超时,则将其自动结束（填充总用时，而无结束时间与最终能力值）
        如果还有在进行的测试，则返回剩余时间最多的那条测试记录
        '''
        unfinished_test_id = None
        tests_info_qs = TestInfo.objects.filter(user_id=user.id)
        now_time = datetime.now()
        total_time_list = []
        for item in tests_info_qs:
            if (not item.end_time):
                if ((now_time - item.start_time) > timedelta(hours=2)):
                    autoFinishTest = TestInfoFinishSer(
                        instance=item, data={'total_time': timedelta(hours=2)})
                    if autoFinishTest.is_valid(raise_exception=True):
                        autoFinishTest.save()
                else:
                    total_time_list.append({
                        'id': item.test_id,
                        'time': (now_time - item.start_time)
                    })

        if len(total_time_list):
            unfinished_test_id = min(total_time_list, key=lambda x: x['time'])['id']
            unfinished_test_obj = TestInfo.objects.get(test_id=unfinished_test_id)
            unfinished_test = TestInfoSerializer(unfinished_test_obj)
        else:
            unfinished_test = None

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        response = jwt_response_payload_handler(token, user, unfinished_test)
        return Response(response, status.HTTP_200_OK)


class userListView(APIView):
    authentication_classes = (TokenAuthentication, )
    permission_classes = (AllowAny, )

    @swagger_auto_schema(responses={200: UserSerializer},
                         security=[],
                         operation_summary='获取所有用户的信息')
    def get(self, req):
        all_user_qs = MyUser.objects.all()
        all_user = UserSerializer(instance=all_user_qs, many=True)
        return Response(all_user.data)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['number', 'password', 'type'],
        properties={
            'number': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
            'type': openapi.Schema(type=openapi.TYPE_NUMBER, enum=[0, 1])
        },
    ),
                         responses={
                             400: 'Bad Request',
                             200: UserSerializer
                         },
                         security=[],
                         operation_summary='用户注册')
    def post(self, req):
        create_user = UserSerializer(data=req.data)
        if create_user.is_valid(raise_exception=True):
            create_user.save()
            return Response(create_user.data, status=status.HTTP_201_CREATED)
        return Response(create_user.errors, status=status.HTTP_400_BAD_REQUEST)


class userDetailView(APIView):
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: UserSerializer
    },
                         operation_summary='获取指定用户的信息')
    def get(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        get_user = UserSerializer(instance=user)
        return Response(get_user.data, status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        description='仅支持修改下列四个用户信息，要修改啥就保留啥，不改的都删掉',
        properties={
            'number': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
            'realname': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING)
        },
    ),
                         responses={
                             400: 'Bad Request',
                             404: 'Not Found',
                             200: UserSerializer
                         },
                         operation_summary='修改指定用户的信息')
    def put(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 若不修改密码，则删除请求体中的数据，以便通过数据校验
        if ('password' in req.data and req.data['password'] == ''):
            del req.data['password']

        update_user = UserSerializer(instance=user, data=req.data, partial=True)
        if (update_user.is_valid(raise_exception=True)):
            update_user.save()
            return Response(update_user.data, status=status.HTTP_200_OK)
        return Response(update_user.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={
        404: 'Not Found',
        204: 'No Content'
    },
                         operation_summary='删除指定用户')
    def delete(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class checkUserTestsView(APIView):
    @swagger_auto_schema(responses={
        200:
        openapi.Response(description='ok',
                         examples={
                             'application/json': {
                                 'isUnfinished': openapi.TYPE_BOOLEAN,
                                 'unfinishedInfo': {
                                     'key': openapi.TYPE_NUMBER,
                                     'start_time': openapi.TYPE_STRING,
                                     'finish_object_test': openapi.TYPE_BOOLEAN
                                 }
                             }
                         })
    },
                         operation_summary='检查用户是否有正在进行的考试')
    def get(self, req):
        unfinished_test_id = None
        now_time = datetime.now()
        user_id = decode_token(req)['user_id']
        tests_info_qs = TestInfo.objects.filter(user_id=user_id)
        total_time_list = []
        for item in tests_info_qs:
            if (not item.end_time):
                if ((now_time - item.start_time) > timedelta(hours=2)):
                    autoFinishTest = TestInfoFinishSer(
                        instance=item, data={'total_time': timedelta(hours=2)})
                    if autoFinishTest.is_valid(raise_exception=True):
                        autoFinishTest.save()
                else:
                    total_time_list.append({
                        'id': item.test_id,
                        'time': (now_time - item.start_time)
                    })

        if len(total_time_list):
            unfinished_test_id = min(total_time_list, key=lambda x: x['time'])['id']
            unfinished_test_obj = TestInfo.objects.get(test_id=unfinished_test_id)
            unfinished_test = TestInfoSerializer(unfinished_test_obj)
            unfinished_test_info = {
                key: val
                for key, val in unfinished_test.data.items()
                if key == 'test_id' or key == 'start_time' or key == 'finish_object_test'
            }
            return Response({
                'isUnfinished': True,
                'unfinishedInfo': unfinished_test_info
            }, status.HTTP_200_OK)
        else:
            return Response({
                'isUnfinished': False,
                'unfinishedInfo': {}
            }, status.HTTP_200_OK)


class userTestsListView(APIView):
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: TestsListSerializer
    },
                         operation_summary='获取用户全部的测试记录')
    def get(self, req):
        try:
            user_id = decode_token(req)['user_id']
            tests_list = TestInfo.objects.filter(user_id=user_id)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        get_tests_list = TestsListSerializer(instance=tests_list, many=True)
        return Response(get_tests_list.data, status.HTTP_200_OK)
