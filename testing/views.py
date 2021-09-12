from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import TestInfo
from .serializers import TestInfoSerializer


class TestInfoView(APIView):
    def post(self, req):
        startTest = TestInfoSerializer(data=req.data)
        if startTest.is_valid(raise_exception=True):
            startTest.save()
            return Response(startTest.data, status.HTTP_201_CREATED)
        return Response(startTest.errors, status.HTTP_400_BAD_REQUEST)


class TestInfoDetailView(APIView):
    def put(self, req, pk):
        try:
            testInfo = TestInfo.objects.get(item_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        updateTest = TestInfoSerializer(instance=testInfo,
                                        data=req.data,
                                        partial=True)
        if updateTest.is_valid(raise_exception=True):
            updateTest.save()
            return Response(updateTest.data, status.HTTP_200_OK)
        return Response(updateTest.errors, status.HTTP_400_BAD_REQUEST)