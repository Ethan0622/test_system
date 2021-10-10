from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import TestItems
from .serializers import itemsAllSerializer, itemsPartSerializer


class itemListView(APIView):
    # 新增试题
    def post(self, req):
        createItem = itemsAllSerializer(data=req.data)
        if createItem.is_valid(raise_exception=True):
            createItem.save()
            return Response(createItem.data, status.HTTP_201_CREATED)
        return Response(createItem.errors, status.HTTP_400_BAD_REQUEST)


class itemListTypeView(APIView):
    # 查看指定类型的题目
    def get(self, req, pk):
        if (pk < 1 or pk > 3):
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            typeItemQS = TestItems.objects.filter(type=pk)
            typeItemList = itemsAllSerializer(instance=typeItemQS, many=True)
            return Response(typeItemList.data, status.HTTP_200_OK)


class itemDetailView(APIView):
    # 获取、修改、删除指定id试题
    def get(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        getItem = itemsPartSerializer(instance=item)
        return Response(getItem.data, status.HTTP_200_OK)

    def put(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        updateItem = itemsAllSerializer(instance=item,
                                        data=req.data,
                                        partial=True)
        if updateItem.is_valid(raise_exception=True):
            updateItem.save()
            return Response(updateItem.data, status.HTTP_200_OK)
        return Response(updateItem.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
