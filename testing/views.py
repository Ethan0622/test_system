import math
from datetime import datetime
from random import choice

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
from catsim.stopping import MinErrorStopper

from users.utils import decode_token
from .utils import get_used_obj_items, get_used_sbj_items, index_map, switch_items_numpy, separate_dict,\
    used_items_ndarry, obj_select_range, select_sbj_item, update_item_difficulty,check_test_will_finish,\
    update_item_exposure, validate_item_total
from .models import InitTestProcess, ObjectTestProcess, SubjectTestProcess, TestInfo, TestSetting
from .serializers import TestSettingSerializer, TestInfoStartSer, TestInfoSerializer, TestInfoFinishSer,\
    ObjTestProcessSerializer,InitTestProcessSerializer, SbjTestProcessSerializer, ItemsPartSerializer,\
    ObjectResultSerializer, SubjectResultSerializer
from users.models import MyUser
from itembank.models import TestItems


class TestSettingView(APIView):
    def get(self, req):
        allTestSettingQs = TestSetting.objects.all()
        allTestSettings = TestSettingSerializer(allTestSettingQs, many=True)
        return Response(allTestSettings.data, status.HTTP_200_OK)


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

        # 先验证并保存考试配置
        # 提供的可能是已有的配置预设，或提供详细的配置参数
        testSettingId = req.data.get('test_setting', None)
        if (not testSettingId):  # 提供的是详细的配置参数
            totalOver = validate_item_total(req.data)
            if type(totalOver) == str:
                return Response({'error': totalOver + '超过现有题量'},
                                status.HTTP_400_BAD_REQUEST)
            elif type(totalOver) == int:
                testSettingId = totalOver
            else:
                saveTestSetting = TestSettingSerializer(data=req.data)
                if saveTestSetting.is_valid(raise_exception=True):
                    saveTestSetting.save()
                    testSettingId = saveTestSetting.data['id']
        req.data['test_setting'] = testSettingId

        firstItem = None
        if user.init_ability != None:  # 考生有初始能力值
            req.data['newest_ability'] = user.init_ability

            selector = MaxInfoSelector()
            numpyArray = switch_items_numpy([], type=1)
            firstItemIndex = selector.select(items=numpyArray,
                                             administered_items=[],
                                             est_theta=user.init_ability)
            firstItemId = numpyArray[firstItemIndex][5]

            firstItemQs = TestItems.objects.get(id=firstItemId)
            firstItem = ItemsPartSerializer(firstItemQs)
        else:  # 考生没有初始能力值
            indexList = range(
                int(len(sortChoiceItems) / 2) - 5,
                int(len(sortChoiceItems) / 2) + 5)
            randomIndex = choice(indexList)
            firstItemQs = TestItems.objects.get(id=sortChoiceItems[randomIndex]['id'])
            firstItem = ItemsPartSerializer(firstItemQs)

        # 手动记录考试开始时间，数据库的auto_add_now不太好用
        req.data['start_time'] = datetime.now()
        startTest = TestInfoStartSer(data=req.data)
        if startTest.is_valid(raise_exception=True):
            startTest.save()
            return Response({
                'testInfo': startTest.data,
                'first_item': firstItem.data
            }, status.HTTP_201_CREATED)
        return Response(startTest.errors, status.HTTP_400_BAD_REQUEST)


class TestInfoDetailView(APIView):
    # 查看考试结果，前提：必须是完整的一次考试
    def get(self, req, pk):
        try:
            testInfo = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if (not testInfo.end_time):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            testId = pk
            objectItemsQs = ObjectTestProcess.objects.filter(test_id=testId)
            subjectItemsQs = SubjectTestProcess.objects.filter(test_id=testId)
            objectItems = ObjectResultSerializer(objectItemsQs, many=True)
            subjectItems = SubjectResultSerializer(subjectItemsQs, many=True)
            return Response(
                {
                    'ability': testInfo.final_ability,
                    'objectItems': objectItems.data,
                    'subjectItems': subjectItems.data
                }, status.HTTP_200_OK)

    # 查看某一次考试的配置信息
    def post(self, req, pk):
        testInfo = TestInfo.objects.get(test_id=pk)
        getTestInfo = TestInfoSerializer(instance=testInfo)
        return Response(getTestInfo.data, status.HTTP_200_OK)

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
        startTime = testInfo.start_time
        endTime = datetime.now()
        req.data['end_time'] = endTime
        req.data['total_time'] = endTime - startTime
        req.data['final_ability'] = testInfo.newest_ability
        finishTest = TestInfoFinishSer(instance=testInfo, data=req.data)
        if finishTest.is_valid(raise_exception=True):
            finishTest.save()
            return Response(finishTest.data, status.HTTP_200_OK)
        return Response(finishTest.errors, status.HTTP_400_BAD_REQUEST)


class ObjectTestProcessView(APIView):
    # 考生完成能力测评后，正式开始客观题测试部分，此接口拿到第一道客观题
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        obj_processes = ObjectTestProcess.objects.filter(test_id=test_id)
        if (not obj_processes):
            selector = MaxInfoSelector()
            numpyArray = switch_items_numpy([], type=1)
            firstItemIndex = selector.select(items=numpyArray,
                                             administered_items=[],
                                             est_theta=user.init_ability)
            firstItemId = numpyArray[firstItemIndex][5]
            firstItemQs = TestItems.objects.get(id=firstItemId)
            first_item = ItemsPartSerializer(firstItemQs)
            return Response(first_item.data, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    # 正式考试过程中做题的记录，记录客观题答案并评判得分，修正能力值。接着给出下一题
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

        testInfo = TestInfo.objects.get(test_id=req.data['test_id'])

        pre_theta = testInfo.newest_ability

        usedObjItems = get_used_obj_items(req.data)

        update_item_exposure(item_id)

        selectRangeDict = obj_select_range(usedObjItems)

        numpyArray = switch_items_numpy(usedObjItems, selectRangeDict['type'],
                                        selectRangeDict['knowledge_id'])
        itemIdList = separate_dict('item_id', usedObjItems)
        judgeList = separate_dict('item_judge', usedObjItems)
        mappedList = index_map(numpyArray, itemIdList)

        selector = MaxInfoSelector()
        estimator = NumericalSearchEstimator()
        stopper = MinErrorStopper(0.2)

        # 根据最大信息量方法为学生选取下一道题
        next_item_index = selector.select(items=numpyArray,
                                          administered_items=mappedList,
                                          est_theta=pre_theta)
        if not (next_item_index is None):
            next_item_id = numpyArray[next_item_index][5]
            next_item_qs = TestItems.objects.get(id=next_item_id)
            next_item = ItemsPartSerializer(next_item_qs)
        else:
            next_item = ItemsPartSerializer({})

        # 测定学生最新能力值
        after_theta = estimator.estimate(items=numpyArray,
                                         administered_items=mappedList,
                                         response_vector=judgeList,
                                         est_theta=pre_theta)
        after_theta = round(after_theta, 8)
        req.data['process_ability'] = after_theta

        # 结束判断，依据最大标准误差<=0.2时（即累计信息量>=25）或做的题目达到40题时允许结束客观题部分
        ad_items_ndarray = used_items_ndarry(numpyArray, itemIdList)
        canStop = stopper.stop(administered_items=ad_items_ndarray, theta=after_theta)
        testSettingId = testInfo.test_setting.id
        testSetting = TestSetting.objects.get(id=testSettingId)
        objectTotal = testSetting.choice_total + testSetting.judge_total
        subjectTotal = testSetting.glossary_total + testSetting.saqs_total + testSetting.discuss_total
        if (len(usedObjItems) >= objectTotal):
            canStop = True
        testWillFinish = False
        testOver = False
        if (len(usedObjItems) == objectTotal - 1 and subjectTotal == 0):
            testWillFinish = True

        update_item_difficulty(req.data)

        # 测试过程中用户最新能力值记录保存，存于测试记录表中
        testInfo.newest_ability = round(after_theta, 8)
        if canStop:
            testInfo.finish_object_test = True
            if subjectTotal == 0:
                testOver = True
        testInfo.save()

        # 测试做题记录保存
        recordTest = ObjTestProcessSerializer(data=req.data)
        if recordTest.is_valid(raise_exception=True):
            recordTest.save()
            if (next_item):
                return Response(
                    {
                        'info': recordTest.data,
                        'next_item': next_item.data,
                        'finishObjTest': canStop,
                        'testWillFinish': testWillFinish,
                        'testAllFinish': testOver
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
            test_info = TestInfo.objects.get(test_id=req.data['test_id'])
            test_info.newest_ability = init_ability
            test_info.save()
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
                    randomIndex = choice(indexList)
                    if (sortChoiceItems[randomIndex]['difficulty'] - difficulty <= 0.5
                        ) and (sortChoiceItems[randomIndex]['id'] not in usedItemsList):
                        init_next_item = sortChoiceItems[randomIndex]
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[randomIndex]['id'])
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
                    randomIndex = choice(indexList)
                    if (difficulty - sortChoiceItems[randomIndex]['difficulty'] <= 0.5
                        ) and (sortChoiceItems[randomIndex]['id'] not in usedItemsList):
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[randomIndex]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_201_CREATED)

    #未完成初始能力测试，需要继续完成时调用此get请求，只返回相应题目
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
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
            randomIndex = choice(indexList)
            firstItemQs = TestItems.objects.get(id=sortChoiceItems[randomIndex]['id'])
            first_item = ItemsPartSerializer(firstItemQs)
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
                    randomIndex = choice(indexList)
                    if (sortChoiceItems[randomIndex]['difficulty'] - difficulty <= 0.5
                        ) and (sortChoiceItems[randomIndex]['id'] not in usedItemsList):
                        init_next_item = sortChoiceItems[randomIndex]
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[randomIndex]['id'])
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
                    randomIndex = choice(indexList)
                    if (difficulty - sortChoiceItems[randomIndex]['difficulty'] <= 0.5
                        ) and (sortChoiceItems[randomIndex]['id'] not in usedItemsList):
                        init_first_item_qs = TestItems.objects.get(
                            id=sortChoiceItems[randomIndex]['id'])
                        init_next_item = ItemsPartSerializer(init_first_item_qs)
                        break
                return Response({'next_item': init_next_item.data}, status.HTTP_200_OK)


class TestContinueView(APIView):
    # 未完成的考试继续进行测试
    def post(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        unfinished_test_id = req.data['unfinished_test_id']
        finishObjTest = TestInfo.objects.get(
            test_id=unfinished_test_id).finish_object_test
        if (user.init_ability):
            if finishObjTest:
                usedSbjItems = get_used_sbj_items(req.data)
                testWillFinish = check_test_will_finish(unfinished_test_id)
                selectedItemId = select_sbj_item(usedSbjItems, unfinished_test_id)
                nextSbjItem = TestItems.objects.get(id=selectedItemId)
                nextItem = ItemsPartSerializer(nextSbjItem)
                return Response(
                    {
                        'next_item': nextItem.data,
                        'testWillFinish': testWillFinish
                    }, status.HTTP_200_OK)
            else:
                usedObjItems = get_used_obj_items(req.data)
                numpyArray = switch_items_numpy(usedObjItems, 'object')
                itemIdList = separate_dict('item_id', usedObjItems)
                mappedList = index_map(numpyArray, itemIdList)

                testId = req.data['unfinished_test_id']
                testInfo = TestInfo.objects.get(test_id=testId)
                pre_theta = testInfo.newest_ability
                selector = MaxInfoSelector()
                firstItemIndex = selector.select(items=numpyArray,
                                                 administered_items=mappedList,
                                                 est_theta=pre_theta)
                firstItemId = numpyArray[firstItemIndex][5]
                firstItemQs = TestItems.objects.get(id=firstItemId)

                testSettingId = testInfo.test_setting.id
                testSetting = TestSetting.objects.get(id=testSettingId)
                objectTotal = testSetting.choice_total + testSetting.judge_total
                subjectTotal = testSetting.glossary_total + testSetting.saqs_total + testSetting.discuss_total
                testWillFinish = False
                if (len(usedObjItems) == objectTotal - 1 and subjectTotal == 0):
                    testWillFinish = True

                nextObjItem = ItemsPartSerializer(firstItemQs)
                return Response(
                    {
                        'next_item': nextObjItem.data,
                        'testWillFinish': testWillFinish
                    }, status.HTTP_200_OK)
        else:
            return Response({
                'init_finished': False,
            }, status.HTTP_200_OK)


class SubjectTestProcessView(APIView):
    # 客观题完成后，请求该接口获取合适的主观题继续测试
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
        testInfo = TestInfo.objects.get(test_id=test_id)
        testWillFinish = False
        testSettingId = testInfo.test_setting.id
        testSetting = TestSetting.objects.get(id=testSettingId)
        subjectTotal = testSetting.glossary_total + testSetting.saqs_total + testSetting.discuss_total
        if subjectTotal <= 1 :
            testWillFinish = True
        else:
            testWillFinish = False
        sbj_processes = SubjectTestProcess.objects.filter(test_id=test_id)
        if (testInfo.finish_object_test and not sbj_processes):
            selectedItemId = select_sbj_item({}, test_id)
            nextSbjItem = TestItems.objects.get(id=selectedItemId)
            nextItem = ItemsPartSerializer(nextSbjItem)
            return Response({
                'next_item': nextItem.data,
                'testWillFinish': testWillFinish
            }, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    # 提交做完的主观题答案，并获取下一道主观题或结束测试
    def post(self, req):
        user_id = decode_token(req)['user_id']
        req.data['user_id'] = user_id
        test_id = req.data.get('test_id')

        testWillFinish = check_test_will_finish(test_id)

        usedSbjItems = get_used_sbj_items(req.data)
        selectedItemId = select_sbj_item(usedSbjItems, test_id)
        if selectedItemId:
            nextSbjItem = TestItems.objects.get(id=selectedItemId)
            testOver = False
            nextItem = ItemsPartSerializer(nextSbjItem)
        else:
            nextItem = ItemsPartSerializer({})
            testOver = True
        # 测试做题记录保存
        recordTest = SbjTestProcessSerializer(data=req.data)
        if recordTest.is_valid(raise_exception=True):
            recordTest.save()
            return Response(
                {
                    'info': recordTest.data,
                    'next_item': nextItem.data,
                    'testWillFinish': testWillFinish,
                    'testAllFinish': testOver
                }, status.HTTP_201_CREATED)
        return Response(recordTest.errors, status.HTTP_400_BAD_REQUEST)