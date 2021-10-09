import math
from random import choice
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator

from users.utils import decodeToken
from .utils import getItemBydifficulty, getUsedItems, indexMap, switchNumpy, separateTuple
from .models import InitTestProcess, TestInfo, ObjectTestProcess
from .serializers import TestInfoSerializer, ObjTestProcessSerializer, InitTestProcessSerializer, ItemInfoSerializer, ItemsPartSerializer
from users.models import MyUser
from itembank.models import TestItems


class TestInfoView(APIView):
    # 开始一次考试
    def post(self, req):
        user_id = decodeToken(req)['user_id']
        req.data['user_id'] = user_id
        user = MyUser.objects.filter(id=user_id).values()
        # 所有选择题
        ChoiceItems = TestItems.objects.filter(type=1).values()
        # 选择题由易到难排序后
        sortChoiceItems = sorted(ChoiceItems, key=lambda x: x['difficulty'])
        first_item = None

        if user[0]['init_ability'] != None:  # 考生有初始能力值
            req.data['newest_ability'] = user[0]['init_ability']

            selector = MaxInfoSelector()
            ChoiceItemsQS = TestItems.objects.filter(type=1)
            allChoiceItems = ItemInfoSerializer(ChoiceItemsQS, many=True)
            numpyArray = switchNumpy(allChoiceItems.data)
            first_item_index = selector.select(
                items=numpyArray,
                administered_items=[],
                est_theta=user[0]['init_ability'])
            first_item_difficulty = numpyArray[first_item_index][1]
            first_item_id = getItemBydifficulty(first_item_difficulty)

            first_item_qs = TestItems.objects.get(id=first_item_id)
            first_item = ItemsPartSerializer(first_item_qs)
        else:  # 考生没有初始能力值
            indexList = range(
                int(len(sortChoiceItems) / 2) - 5,
                int(len(sortChoiceItems) / 2) + 5)
            random_index = choice(indexList)
            first_item_qs = TestItems.objects.get(
                id=sortChoiceItems[random_index]['id'])
            first_item = ItemsPartSerializer(first_item_qs)

        startTest = TestInfoSerializer(data=req.data)
        if startTest.is_valid(raise_exception=True):
            startTest.save()
            return Response(
                {
                    'testInfo': startTest.data,
                    'first_item': first_item.data
                }, status.HTTP_201_CREATED)
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
    # 正式考试过程中做题的记录
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

        first_item_index = selector.select(items=numpyArray,
                                           administered_items=mappedList,
                                           est_theta=pre_theta)
        first_item_difficulty = numpyArray[first_item_index][1]
        first_item_id = getItemBydifficulty(first_item_difficulty)

        first_item_qs = TestItems.objects.get(id=first_item_id)
        next_item = ItemsPartSerializer(first_item_qs)

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


class InitTestProcessView(APIView):
    # 第一次考试，初始能力评估阶段答题处理
    def post(self, req):
        user_id = decodeToken(req)['user_id']
        item_id = req.data['item_id']
        item = TestItems.objects.filter(id=item_id).values()
        if item[0]['correct'] == req.data['answer']:
            judge = True
        else:
            judge = False
        req.data['judge'] = judge
        recordInitTest = InitTestProcessSerializer(data=req.data)
        if recordInitTest.is_valid(raise_exception=True):
            recordInitTest.save()

        InitTested = InitTestProcess.objects.filter(
            test_id=req.data['test_id']).values()
        if (len(InitTested) == 5):
            trueCount = 0
            for testesInfo in InitTested:
                if testesInfo['judge'] == True:
                    trueCount += 1
            if (trueCount == 0 or trueCount == 5):
                init_ability_log = math.log(
                    (trueCount + 0.5) / (5.5 - trueCount))
            else:
                init_ability_log = math.log(trueCount / (5 - trueCount))
            user = MyUser.objects.get(user_id=user_id)
            init_ability = round(init_ability_log, 8)
            user.init_ability = init_ability
            user.save()
            return Response(
                {
                    'msg': '初始能力评估已完成，可以开始正式考试！',
                    'init_ability': init_ability
                }, status.HTTP_200_OK)
        else:
            # 所有选择题
            ChoiceItems = TestItems.objects.filter(type=1).values()
            # 选择题由易到难排序后
            sortChoiceItems = sorted(ChoiceItems,
                                     key=lambda x: x['difficulty'])

            initUsedItems = []
            for testedInfo in InitTested:
                item_id = testedInfo['item_id_id']
                item = TestItems.objects.filter(id=item_id).values()
                initUsedItems.append(
                    (item_id, item[0]['difficulty'], testedInfo['judge']))

            usedItemsList = separateTuple(0, initUsedItems)
            if initUsedItems[-1][2]:  # 最新的一题做对
                item_id = initUsedItems[-1][0]
                difficulty = initUsedItems[-1][1]
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index + 11 > len(sortChoiceItems):
                    indexList = range(index + 1, len(sortChoiceItems))
                else:
                    indexList = range(index + 1, index + 11)
                init_first_item_qs = None
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (sortChoiceItems[random_index]['difficulty'] -
                            difficulty <=
                            0.5) and (sortChoiceItems[random_index]['id']
                                      not in usedItemsList):
                        init_next_item = sortChoiceItems[random_index]
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(
                            init_first_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_200_OK)

            else:  # 最新一题做错
                item_id = initUsedItems[-1][0]
                difficulty = initUsedItems[-1][1]
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index - 11 < 0:
                    indexList = range(0, index - 1)
                else:
                    indexList = range(index - 11, index - 1)
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (difficulty -
                            sortChoiceItems[random_index]['difficulty'] <=
                            0.5) and (sortChoiceItems[random_index]['id']
                                      not in usedItemsList):
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(
                            init_first_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_200_OK)
