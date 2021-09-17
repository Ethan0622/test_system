from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny

from .models import MyUser
from .serializers import UserSerializer


class userListView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (AllowAny,)
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
