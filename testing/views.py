import math
from datetime import datetime
from random import choice

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
from catsim.stopping import MinErrorStopper

from users.utils import decode_token
from .utils import get_item_by_difficulty, get_used_items, index_map, switch_items_numpy, separate_dict, used_items_ndarry, select_range, update_item_difficulty
from .models import InitTestProcess, TestInfo
from .serializers import TestInfoStartSer, TestInfoSerializer, TestInfoFinishSer, ObjTestProcessSerializer, InitTestProcessSerializer, ItemInfoSerializer, ItemsPartSerializer
from users.models import MyUser
from itembank.models import TestItems


class TestInfoView(APIView):
    # 开始一次考试
    def post(self, req):
        user_id = decode_token(req)['user_id']
        req.data['user_id'] = user_id
        user = MyUser.objects.get(id=user_id)
        # 所有选择题
        ChoiceItems = TestItems.objects.filter(type=1).values()
        # 选择题由易到难排序后
        sortChoiceItems = sorted(ChoiceItems, key=lambda x: x['difficulty'])
        first_item = None

        if user.init_ability != None:  # 考生有初始能力值
            req.data['newest_ability'] = user.init_ability

            selector = MaxInfoSelector()
            numpyArray = switch_items_numpy([], type=1)
            first_item_index = selector.select(items=numpyArray,
                                               administered_items=[],
                                               est_theta=user.init_ability)
            first_item_difficulty = numpyArray[first_item_index][1]
            first_item_id = get_item_by_difficulty(first_item_difficulty)

            first_item_qs = TestItems.objects.get(id=first_item_id)
            first_item = ItemsPartSerializer(first_item_qs)
        else:  # 考生没有初始能力值
            indexList = range(
                int(len(sortChoiceItems) / 2) - 5,
                int(len(sortChoiceItems) / 2) + 5)
            random_index = choice(indexList)
            first_item_qs = TestItems.objects.get(id=sortChoiceItems[random_index]['id'])
            first_item = ItemsPartSerializer(first_item_qs)

        # 手动记录考试开始时间，数据库的auto_add_now不太好用
        req.data['start_time'] = datetime.now()
        startTest = TestInfoStartSer(data=req.data)
        if startTest.is_valid(raise_exception=True):
            startTest.save()
            return Response({
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
        updateTest = TestInfoSerializer(instance=testInfo, data=req.data, partial=True)
        if updateTest.is_valid(raise_exception=True):
            updateTest.save()
            return Response(updateTest.data, status.HTTP_200_OK)
        return Response(updateTest.errors, status.HTTP_400_BAD_REQUEST)


class TestFinishView(APIView):
    # 考试结束信息,提交结束时间以及计算最后能力值
    def post(self, req, pk):
        try:
            testInfo = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        # 结束时间记录，并计算考试时长
        start_time = testInfo.start_time
        end_time = datetime.now()
        req.data['end_time'] = end_time
        req.data['total_time'] = end_time - start_time
        req.data['final_ability'] = testInfo.newest_ability
        finishTest = TestInfoFinishSer(instance=testInfo, data=req.data)
        if finishTest.is_valid(raise_exception=True):
            finishTest.save()
            return Response(finishTest.data, status.HTTP_200_OK)
        return Response(finishTest.errors, status.HTTP_400_BAD_REQUEST)


class TestProcessView(APIView):
    # 正式考试过程中做题的记录
    def post(self, req):
        user_id = decode_token(req)['user_id']
        item_id = req.data['item_id']
        item = TestItems.objects.get(id=item_id)
        if item.correct == req.data['answer']:
            judge = True
        else:
            judge = False
        req.data['judge'] = judge
        req.data['user_id'] = user_id

        pre_theta = TestInfo.objects.get(test_id=req.data['test_id']).newest_ability

        usedItems = get_used_items(req.data)

        selectRangeDict = select_range(usedItems)

        numpyArray = switch_items_numpy(usedItems, selectRangeDict['type'],
                                        selectRangeDict['knowledge_id'])
        itemIdList = separate_dict('item_id', usedItems)
        judgeList = separate_dict('item_judge', usedItems)
        mappedList = index_map(numpyArray, itemIdList)

        selector = MaxInfoSelector()
        estimator = NumericalSearchEstimator()
        stopper = MinErrorStopper(0.2)

        # 根据最大信息量方法为学生选取下一道题
        next_item_index = selector.select(items=numpyArray,
                                          administered_items=mappedList,
                                          est_theta=pre_theta)
        if next_item_index:
            next_item_difficulty = numpyArray[next_item_index][1]
            next_item_id = get_item_by_difficulty(next_item_difficulty)
            next_item_qs = TestItems.objects.get(id=next_item_id)
            next_item = ItemsPartSerializer(next_item_qs)
        else:
            pass

        # 测定学生最新能力值
        after_theta = estimator.estimate(items=numpyArray,
                                         administered_items=mappedList,
                                         response_vector=judgeList,
                                         est_theta=pre_theta)
        req.data['process_ability'] = after_theta

        # 结束判断，依据最大标准误差<=0.2时（即累计信息量>=25）或做的题目达到40题时允许结束客观题部分
        ad_items_ndarray = used_items_ndarry(numpyArray, itemIdList)
        canStop = stopper.stop(administered_items=ad_items_ndarray, theta=after_theta)
        if (len(usedItems) >= 40):
            canStop = True

        update_item_difficulty(req.data)

        # 测试过程中用户最新能力值记录保存，存于测试记录表中
        testInfo = TestInfo.objects.get(test_id=req.data['test_id'])
        testInfo.newest_ability = round(after_theta, 8)
        testInfo.save()

        # 测试做题记录保存
        recordTest = ObjTestProcessSerializer(data=req.data)
        if recordTest.is_valid(raise_exception=True):
            recordTest.save()
            return Response(
                {
                    'info': recordTest.data,
                    "next_item": next_item.data or {},
                    'finishObjTest': canStop
                }, status.HTTP_201_CREATED)

        return Response(recordTest.errors, status.HTTP_400_BAD_REQUEST)


class InitTestProcessView(APIView):
    # 第一次考试，初始能力评估阶段答题处理，记录答题并返回下一道题目
    def post(self, req):
        user_id = decode_token(req)['user_id']
        item_id = req.data['item_id']
        item = TestItems.objects.get(id=item_id)
        if item.correct == req.data['answer']:
            judge = True
        else:
            judge = False
        req.data['judge'] = judge
        recordInitTest = InitTestProcessSerializer(data=req.data)
        if recordInitTest.is_valid(raise_exception=True):
            recordInitTest.save()
        
        update_item_difficulty(req.data)

        InitTested = InitTestProcess.objects.filter(test_id=req.data['test_id']).values(
            'id', 'test_id', 'item_id', 'judge')
        if (len(InitTested) == 5):
            trueCount = 0
            for testedInfo in InitTested:
                if testedInfo['judge'] == True:
                    trueCount += 1
            if (trueCount == 0 or trueCount == 5):
                init_ability_log = math.log((trueCount + 0.5) / (5.5 - trueCount))
            else:
                init_ability_log = math.log(trueCount / (5 - trueCount))
            user = MyUser.objects.get(id=user_id)
            init_ability = round(init_ability_log, 8)
            user.init_ability = init_ability
            user.save()
            return Response({
                'init_finished': True,
                'init_ability': init_ability
            }, status.HTTP_201_CREATED)
        else:
            # 所有选择题
            ChoiceItems = TestItems.objects.filter(type=1).values()
            # 选择题由易到难排序后
            sortChoiceItems = sorted(ChoiceItems, key=lambda x: x['difficulty'])

            initUsedItems = []
            for testedInfo in InitTested:
                item_id = testedInfo['item_id']
                item = TestItems.objects.get(id=item_id)
                initUsedItems.append({
                    'item_id': item_id,
                    'item_difficulty': item.difficulty,
                    'item_judge': testedInfo['judge']
                })
            usedItemsList = separate_dict('item_id', initUsedItems)
            if initUsedItems[-1]['item_judge']:  # 最新的一题做对
                item_id = initUsedItems[-1]['item_id']
                difficulty = initUsedItems[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index + 11 > len(sortChoiceItems):
                    indexList = range(index + 1, len(sortChoiceItems))
                else:
                    indexList = range(index + 1, index + 11)
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (sortChoiceItems[random_index]['difficulty'] - difficulty <= 0.5
                        ) and (sortChoiceItems[random_index]['id'] not in usedItemsList):
                        init_next_item = sortChoiceItems[random_index]
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_201_CREATED)
            else:  # 最新一题做错
                item_id = initUsedItems[-1]['item_id']
                difficulty = initUsedItems[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index - 11 < 0:
                    indexList = range(0, index - 1)
                else:
                    indexList = range(index - 11, index - 1)
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (difficulty - sortChoiceItems[random_index]['difficulty'] <= 0.5
                        ) and (sortChoiceItems[random_index]['id'] not in usedItemsList):
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_201_CREATED)

    #未完成初始能力测试，需要继续完成时调用此get请求，只返回相应题目
    def get(self, req):
        test_id = req.GET.get('test_id')
        InitTested = InitTestProcess.objects.filter(test_id=test_id).values(
            'id', 'test_id', 'item_id', 'judge')
        # 所有选择题
        ChoiceItems = TestItems.objects.filter(type=1).values()
        # 选择题由易到难排序后
        sortChoiceItems = sorted(ChoiceItems, key=lambda x: x['difficulty'])
        initUsedItems = []
        for testedInfo in InitTested:
            item_id = testedInfo['item_id']
            item = TestItems.objects.get(id=item_id)
            initUsedItems.append({
                'item_id': item_id,
                'item_difficulty': item.difficulty,
                'item_judge': testedInfo['judge']
            })
        if (not initUsedItems):
            indexList = range(
                int(len(sortChoiceItems) / 2) - 5,
                int(len(sortChoiceItems) / 2) + 5)
            random_index = choice(indexList)
            first_item_qs = TestItems.objects.get(id=sortChoiceItems[random_index]['id'])
            first_item = ItemsPartSerializer(first_item_qs)
            return Response({'next_item': first_item.data}, status.HTTP_200_OK)
        else:
            usedItemsList = separate_dict('item_id', initUsedItems)
            if initUsedItems[-1]['item_judge']:  # 最新的一题做对
                item_id = initUsedItems[-1]['item_id']
                difficulty = initUsedItems[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index + 11 > len(sortChoiceItems):
                    indexList = range(index + 1, len(sortChoiceItems))
                else:
                    indexList = range(index + 1, index + 11)
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (sortChoiceItems[random_index]['difficulty'] - difficulty <= 0.5
                        ) and (sortChoiceItems[random_index]['id'] not in usedItemsList):
                        init_next_item = sortChoiceItems[random_index]
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break
                return Response({'next_item': init_next_item.data}, status.HTTP_200_OK)
            else:  # 最新一题做错
                item_id = initUsedItems[-1]['item_id']
                difficulty = initUsedItems[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sortChoiceItems.index(item[0])
                if index - 11 < 0:
                    indexList = range(0, index - 1)
                else:
                    indexList = range(index - 11, index - 1)
                init_next_item = None
                while True:
                    random_index = choice(indexList)
                    if (difficulty - sortChoiceItems[random_index]['difficulty'] <= 0.5
                        ) and (sortChoiceItems[random_index]['id'] not in usedItemsList):
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break
                return Response({'next_item': init_next_item.data}, status.HTTP_200_OK)


class TestContinueView(APIView):
    # 未完成的考试继续进行测试
    def post(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        if (user.init_ability):
            usedItems = get_used_items(req.data)
            numpyArray = switch_items_numpy(usedItems, 'object')
            itemIdList = separate_dict('item_id', usedItems)
            mappedList = index_map(numpyArray, itemIdList)

            test_id = req.data['unfinished_test_id']
            pre_theta = TestInfo.objects.get(test_id=test_id).newest_ability
            selector = MaxInfoSelector()
            first_item_index = selector.select(items=numpyArray,
                                               administered_items=mappedList,
                                               est_theta=pre_theta)
            first_item_difficulty = numpyArray[first_item_index][1]
            first_item_id = get_item_by_difficulty(first_item_difficulty)
            first_item_qs = TestItems.objects.get(id=first_item_id)
            next_item = ItemsPartSerializer(first_item_qs)
            return Response({"next_item": next_item.data}, status.HTTP_200_OK)
        else:
            return Response({
                'init_finished': False,
            }, status.HTTP_200_OK)
