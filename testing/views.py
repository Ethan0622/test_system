from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from users.utils import decodeToken
from .models import TestInfo
from .serializers import TestInfoSerializer
from users.models import MyUser

class TestInfoView(APIView):
    # 开始一次考试
    def post(self, req):   
        user_id = decodeToken(req)['user_id']
        req.data['user_id'] = user_id
        user = MyUser.objects.filter(id = user_id).values()
        if user[0]['init_ability'] != None:
            req.data['newest_ability'] = user[0]['init_ability']
        startTest = TestInfoSerializer(data=req.data)
        if startTest.is_valid(raise_exception=True):
            startTest.save()
            return Response(startTest.data, status.HTTP_201_CREATED)
        return Response(startTest.errors, status.HTTP_400_BAD_REQUEST)


class TestInfoDetailView(APIView):
    # 考试过程中信息修改，考试结束等信息的提交
    def put(self, req, pk):
        # user_id = decodeToken(req)['user_id']
        # req.data['user_id'] = user_id
        try:
            testInfo = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        updateTest = TestInfoSerializer(instance=testInfo,
                                        data=req.data,
                                        partial=True)
        if updateTest.is_valid(raise_exception=True):
            updateTest.save()
            return Response(updateTest.data, status.HTTP_200_OK)
        return Response(updateTest.errors, status.HTTP_400_BAD_REQUEST)