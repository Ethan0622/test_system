from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import ChoiceItems, TFItems
from .serializer import choiceAllSerializer, TFAllSerializer


class itemListView(APIView):
    # 新增试题
    def post(self, req):
        if 'type' in req.data and req.data['type'] == 1:
            createChoiceItem = choiceAllSerializer(data=req.data)
            if createChoiceItem.is_valid(raise_exception=True):
                createChoiceItem.save()
                return Response(createChoiceItem.data, status.HTTP_201_CREATED)
            return Response(createChoiceItem.errors,
                            status.HTTP_400_BAD_REQUEST)
        elif 'type' in req.data and req.data['type'] == 2:
            createTFItem = TFAllSerializer(data=req.data)
            if createTFItem.is_valid(raise_exception=True):
                createTFItem.save()
                return Response(createTFItem.data, status.HTTP_201_CREATED)
            return Response(createTFItem.errors, status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                "check if you post a 'type' [1, 2, 3] or the 'type' is string",
                status.HTTP_400_BAD_REQUEST)


class itemDetailView(APIView):
    # 修改、删除指定id试题，
    def put(self, req, pk):
        if 'type' in req.data and req.data['type'] == 1:
            try:
                item = ChoiceItems.objects.get(id=pk)
            except ChoiceItems.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            updateChoiceItem = choiceAllSerializer(instance=item,
                                                   data=req.data,
                                                   partial=True)
            if updateChoiceItem.is_valid(raise_exception=True):
                updateChoiceItem.save()
                return Response(updateChoiceItem.data, status.HTTP_200_OK)
            return Response(updateChoiceItem.errors,
                            status.HTTP_400_BAD_REQUEST)
        elif 'type' in req.data and req.data['type'] == 2:
            try:
                item = TFItems.objects.get(id=pk)
            except TFItems.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            updateTFItem = TFAllSerializer(instance=item,
                                           data=req.data,
                                           partial=True)
            if updateTFItem.is_valid(raise_exception=True):
                updateTFItem.save()
                return Response(updateTFItem.data, status.HTTP_200_OK)
            return Response(updateTFItem.errors, status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                "check if you post a 'type' [1, 2, 3] or the 'type' is string",
                status.HTTP_400_BAD_REQUEST)

    def delete(self, req, pk):
        if 'type' in req.data and req.data['type'] == 1:
            try:
                item = ChoiceItems.objects.get(id=pk)
            except ChoiceItems.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif 'type' in req.data and req.data['type'] == 2:
            try:
                item = TFItems.objects.get(id=pk)
            except TFItems.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                "check if you post a 'type' [1, 2, 3] or the 'type' is string",
                status.HTTP_400_BAD_REQUEST)
