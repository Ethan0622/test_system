from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator

from users.utils import decodeToken
from .utils import getItemBydiffculty, getUsedItems, indexMap, switchNumpy, separateTuple
from .models import TestInfo, ObjectTestProcess
from .serializers import TestInfoSerializer, ObjTestProcessSerializer, ItemInfoSerializer, ItemsPartSerializer
from users.models import MyUser
from itembank.models import TestItems


class TestInfoView(APIView):
    # 开始一次考试
    def post(self, req):
        user_id = decodeToken(req)['user_id']
        req.data['user_id'] = user_id
        user = MyUser.objects.filter(id=user_id).values()
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


class TestProcessView(APIView):
    # 考试过程中做题的记录
    def post(self, req):
        user_id = decodeToken(req)['user_id']
        item_id = req.data['item_id']
        item = TestItems.objects.filter(id=item_id).values()
        if item[0]['correct'] == req.data['answer']:
            judge = True
        else:
            judge = False
        req.data['judge'] = judge
        req.data['user_id'] = user_id

        pre_theta = TestInfo.objects.filter(
            test_id=req.data['test_id']).values()[0]['newest_ability']

        usedItems = getUsedItems(req.data)

        itemsQS = TestItems.objects.all()
        allItems = ItemInfoSerializer(itemsQS, many=True)
        numpyArray = switchNumpy(allItems.data)
        itemIdList = separateTuple(0, usedItems)
        judgeList = separateTuple(2, usedItems)
        mappedList = indexMap(numpyArray, itemIdList)

        selector = MaxInfoSelector()
        estimator = NumericalSearchEstimator()

        next_item_index = selector.select(items=numpyArray,
                                          administered_items=mappedList,
                                          est_theta=pre_theta)
        next_item_diffculty = numpyArray[next_item_index][1]
        next_item_id = getItemBydiffculty(next_item_diffculty)

        next_item_qs = TestItems.objects.get(id=next_item_id)
        next_item = ItemsPartSerializer(next_item_qs)

        after_theta = estimator.estimate(items=numpyArray,
                                         administered_items=mappedList,
                                         response_vector=judgeList,
                                         est_theta=pre_theta)
        req.data['process_ability'] = after_theta

        testInfo = TestInfo.objects.get(test_id=req.data['test_id'])
        testInfo.newest_ability = round(after_theta, 8)
        testInfo.save()

        recordTest = ObjTestProcessSerializer(data=req.data)
        if recordTest.is_valid(raise_exception=True):
            recordTest.save()
            return Response(
                {
                    'info': recordTest.data,
                    "next_item": next_item.data
                }, status.HTTP_201_CREATED)

        return Response(recordTest.errors, status.HTTP_400_BAD_REQUEST)
