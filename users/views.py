from datetime import datetime, timedelta

from django.db.models.fields import NullBooleanField
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework_jwt.settings import api_settings

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
        testsInfo = TestInfo.objects.filter(user_id=user.id)
        now_time = datetime.now()
        totalTimeList = []
        for item in testsInfo:
            if (not item.end_time):
                if ((now_time - item.start_time) > timedelta(hours=2)):
                    autoFinishTest = TestInfoFinishSer(
                        instance=item, data={'total_time': timedelta(hours=2)})
                    if autoFinishTest.is_valid(raise_exception=True):
                        autoFinishTest.save()
                else:
                    totalTimeList.append({
                        'id': item.test_id,
                        'time': (now_time - item.start_time)
                    })

        if len(totalTimeList):
            unfinished_test_id = min(totalTimeList, key=lambda x: x['time'])['id']
            unfinishedTest = TestInfo.objects.get(test_id=unfinished_test_id)
            unfinished_test = TestInfoSerializer(unfinishedTest)
        else:
            unfinished_test = None

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        response = jwt_response_payload_handler(token, user, unfinished_test)
        return Response(response, status.HTTP_200_OK)


class userListView(APIView):
    authentication_classes = (TokenAuthentication, )
    permission_classes = (AllowAny, )
    '''
    获取所有用户信息&加入新用户
    '''
    def get(self, req):
        qs = MyUser.objects.all()
        allUser = UserSerializer(instance=qs, many=True)
        return Response(allUser.data)

    def post(self, req):
        createUser = UserSerializer(data=req.data)
        if createUser.is_valid(raise_exception=True):
            createUser.save()
            return Response(createUser.data, status=status.HTTP_201_CREATED)
        return Response(createUser.errors, status=status.HTTP_400_BAD_REQUEST)


class userDetailView(APIView):
    '''
    指定id的数据查询、修改、删除
    '''
    def get(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        getUser = UserSerializer(instance=user)
        return Response(getUser.data, status.HTTP_200_OK)

    def put(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 若不修改密码，则删除请求体中的数据，以便通过数据校验
        if ('password' in req.data and req.data['password'] == ''):
            del req.data['password']

        updateUser = UserSerializer(instance=user, data=req.data, partial=True)
        if (updateUser.is_valid(raise_exception=True)):
            updateUser.save()
            return Response(updateUser.data, status=status.HTTP_200_OK)
        return Response(updateUser.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, req, pk):
        try:
            user = MyUser.objects.get(id=pk)
        except MyUser.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class checkUserTestsView(APIView):
    def get(self, req):
        unfinished_test_id = None
        now_time = datetime.now()
        user_id = decode_token(req)['user_id']
        testsInfo = TestInfo.objects.filter(user_id=user_id)
        totalTimeList = []
        for item in testsInfo:
            if (not item.end_time):
                if ((now_time - item.start_time) > timedelta(hours=2)):
                    autoFinishTest = TestInfoFinishSer(
                        instance=item, data={'total_time': timedelta(hours=2)})
                    if autoFinishTest.is_valid(raise_exception=True):
                        autoFinishTest.save()
                else:
                    totalTimeList.append({
                        'id': item.test_id,
                        'time': (now_time - item.start_time)
                    })

        if len(totalTimeList):
            unfinished_test_id = min(totalTimeList, key=lambda x: x['time'])['id']
            unfinishedTest = TestInfo.objects.get(test_id=unfinished_test_id)
            unfinished_test = TestInfoSerializer(unfinishedTest)
            unfinished_test_info = {
                key: val
                for key, val in unfinished_test.data.items()
                if key == 'test_id' or key == 'start_time'
            }
            return Response(
                {
                    'unfinishTest': True,
                    'unfinished_test': unfinished_test_info
                }, status.HTTP_200_OK)
        else:
            return Response({
                'unfinishTest': False,
                'unfinished_test': {}
            }, status.HTTP_200_OK)


class userTestsListView(APIView):
    '''
    查询一个学生全部的测验记录
    '''
    def get(self, req):
        try:
            user_id = decode_token(req)['user_id']
            testsList = TestInfo.objects.filter(user_id=user_id)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        getTestsList = TestsListSerializer(instance=testsList, many=True)
        return Response(getTestsList.data, status.HTTP_200_OK)
