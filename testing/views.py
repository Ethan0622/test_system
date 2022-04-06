import math
from datetime import datetime
from random import choice

from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from catsim.selection import MaxInfoSelector
from catsim.estimation import NumericalSearchEstimator
from catsim.stopping import MinErrorStopper
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

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
    @swagger_auto_schema(responses={200: TestSettingSerializer},
                         operation_summary='获取已有的考试预设')
    def get(self, req):
        all_testsettings_qs = TestSetting.objects.all()
        all_testsettings = TestSettingSerializer(all_testsettings_qs, many=True)
        return Response(all_testsettings.data, status.HTTP_200_OK)


class TestInfoView(APIView):
    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        description='任选其一：提供test_setting的id或其余五个详细参数',
        properties={
            'test_setting': openapi.Schema(type=openapi.TYPE_NUMBER),
            'choice_total': openapi.Schema(type=openapi.TYPE_NUMBER),
            'judge_total': openapi.Schema(type=openapi.TYPE_NUMBER),
            'glossary_total': openapi.Schema(type=openapi.TYPE_NUMBER),
            'saqs_total': openapi.Schema(type=openapi.TYPE_NUMBER),
            'discuss_total': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             201: TestInfoStartSer
                         },
                         operation_summary='开始一次考试')
    def post(self, req):
        user_id = decode_token(req)['user_id']
        req.data['user_id'] = user_id
        user = MyUser.objects.get(id=user_id)
        # 所有选择题
        choice_items = TestItems.objects.filter(type=1).values()
        # 选择题由易到难排序后
        sort_choice_items = sorted(choice_items, key=lambda x: x['difficulty'])

        # 先验证并保存考试配置
        # 提供的可能是已有的配置预设，或提供详细的配置参数
        testsetting_id = req.data.get('test_setting', None)
        if (not testsetting_id):  # 提供的是详细的配置参数
            total_over = validate_item_total(req.data)
            if type(total_over) == str:
                return Response({'error': total_over + '超过现有题量'},
                                status.HTTP_400_BAD_REQUEST)
            elif type(total_over) == int:
                testsetting_id = total_over
            else:
                save_testsetting = TestSettingSerializer(data=req.data)
                if save_testsetting.is_valid(raise_exception=True):
                    save_testsetting.save()
                    testsetting_id = save_testsetting.data['id']
        req.data['test_setting'] = testsetting_id

        first_item = None
        if user.init_ability != None:  # 考生有初始能力值
            req.data['newest_ability'] = user.init_ability

            selector = MaxInfoSelector()
            numpy_array = switch_items_numpy([], type=1)
            first_item_index = selector.select(items=numpy_array,
                                               administered_items=[],
                                               est_theta=user.init_ability)

            first_item_id = numpy_array[first_item_index][5]
            first_item_obj = TestItems.objects.get(id=first_item_id)
            first_item = ItemsPartSerializer(first_item_obj)
        else:  # 考生没有初始能力值
            index_list = range(
                int(len(sort_choice_items) / 2) - 5,
                int(len(sort_choice_items) / 2) + 5)
            random_index = choice(index_list)
            first_item_obj = TestItems.objects.get(
                id=sort_choice_items[random_index]['id'])
            first_item = ItemsPartSerializer(first_item_obj)

        # 手动记录考试开始时间，数据库的auto_add_now不太好用
        req.data['start_time'] = datetime.now()
        start_test = TestInfoStartSer(data=req.data)
        if start_test.is_valid(raise_exception=True):
            start_test.save()
            return Response({
                'testInfo': start_test.data,
                'first_item': first_item.data
            }, status.HTTP_201_CREATED)
        return Response(start_test.errors, status.HTTP_400_BAD_REQUEST)


class TestInfoDetailView(APIView):
    # 查看考试结果，前提：必须是完整的一次考试
    @swagger_auto_schema(responses={
        400:
        'Bad Request',
        404:
        'Not Found',
        200:
        openapi.Response(description='OK',
                         examples={
                             'application/json': {
                                 'ability': openapi.TYPE_NUMBER,
                                 'objectItems': [{}],
                                 'subjectItems': [{}],
                             }
                         })
    },
                         operation_summary='查看一次考试的结果反馈（该次考试必须完成）')
    def get(self, req, pk):
        try:
            test_info = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if (not test_info.end_time):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            test_id = pk
            object_items_qs = ObjectTestProcess.objects.filter(test_id=test_id)
            subject_items_qs = SubjectTestProcess.objects.filter(test_id=test_id)
            object_items = ObjectResultSerializer(object_items_qs, many=True)
            subject_items = SubjectResultSerializer(subject_items_qs, many=True)
            return Response(
                {
                    'ability': test_info.final_ability,
                    'objectItems': object_items.data,
                    'subjectItems': subject_items.data
                }, status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: TestInfoSerializer},
                         operation_summary='查看某一次考试的配置信息')
    def post(self, req, pk):
        test_info = TestInfo.objects.get(test_id=pk)
        get_test_info = TestInfoSerializer(instance=test_info)
        return Response(get_test_info.data, status.HTTP_200_OK)

    @swagger_auto_schema(operation_summary='考试信息的修改，一般不使用该接口', deprecated=True)
    def put(self, req, pk):
        try:
            test_info = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        update_test_info = TestInfoSerializer(instance=test_info,
                                              data=req.data,
                                              partial=True)
        if update_test_info.is_valid(raise_exception=True):
            update_test_info.save()
            return Response(update_test_info.data, status.HTTP_200_OK)
        return Response(update_test_info.errors, status.HTTP_400_BAD_REQUEST)


class TestFinishView(APIView):
    # 考试结束信息,提交结束时间以及计算最后能力值
    @swagger_auto_schema(responses={200: TestInfoFinishSer}, operation_summary='结束一次考试')
    def post(self, req, pk):
        try:
            test_info = TestInfo.objects.get(test_id=pk)
        except TestInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        # 结束时间记录，并计算考试时长
        start_time = test_info.start_time
        end_time = datetime.now()
        req.data['end_time'] = end_time
        req.data['total_time'] = end_time - start_time
        req.data['final_ability'] = test_info.newest_ability
        finish_test = TestInfoFinishSer(instance=test_info, data=req.data)
        if finish_test.is_valid(raise_exception=True):
            finish_test.save()
            return Response(finish_test.data, status.HTTP_200_OK)
        return Response(finish_test.errors, status.HTTP_400_BAD_REQUEST)


class ObjectTestProcessView(APIView):
    test_id = openapi.Parameter('test_id',
                                required=True,
                                in_=openapi.IN_QUERY,
                                description='考试记录Id',
                                type=openapi.TYPE_NUMBER)

    @swagger_auto_schema(manual_parameters=[test_id],
                         responses={
                             200: ItemsPartSerializer,
                         },
                         operation_summary='正式测试时获取第一道客观题')
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        obj_processes = ObjectTestProcess.objects.filter(test_id=test_id)
        if (not obj_processes):
            selector = MaxInfoSelector()
            numpy_array = switch_items_numpy([], type=1)
            first_item_index = selector.select(items=numpy_array,
                                               administered_items=[],
                                               est_theta=user.init_ability)
            first_item_id = numpy_array[first_item_index][5]
            first_item_qs = TestItems.objects.get(id=first_item_id)
            first_item = ItemsPartSerializer(instance=first_item_qs)
            return Response(first_item.data, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['item_id', 'answer', 'test_id'],
        properties={
            'item_id': openapi.Schema(type=openapi.TYPE_NUMBER),
            'answer': openapi.Schema(type=openapi.TYPE_STRING),
            'test_id': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    ),
                         responses={
                             400:
                             'Bad Request',
                             201:
                             openapi.Response(description='OK',
                                              examples={
                                                  'application/json': {
                                                      'info': {},
                                                      'next_item': {},
                                                      'finishObjTest':
                                                      openapi.TYPE_BOOLEAN,
                                                      'testWillFinish':
                                                      openapi.TYPE_BOOLEAN,
                                                      'testAllFinish':
                                                      openapi.TYPE_BOOLEAN
                                                  }
                                              })
                         },
                         operation_summary='提交客观题答案，并获取下一题')

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

        test_info = TestInfo.objects.get(test_id=req.data['test_id'])

        pre_theta = test_info.newest_ability

        used_obj_items = get_used_obj_items(req.data)

        update_item_exposure(item_id)

        select_range_dict = obj_select_range(used_obj_items)

        numpy_array = switch_items_numpy(used_obj_items, select_range_dict['type'],
                                         select_range_dict['knowledge_id'])
        item_id_list = separate_dict('item_id', used_obj_items)
        judge_list = separate_dict('item_judge', used_obj_items)
        mapped_list = index_map(numpy_array, item_id_list)

        selector = MaxInfoSelector()
        estimator = NumericalSearchEstimator()
        stopper = MinErrorStopper(0.2)

        # 根据最大信息量方法为学生选取下一道题
        next_item_index = selector.select(items=numpy_array,
                                          administered_items=mapped_list,
                                          est_theta=pre_theta)
        if not (next_item_index is None):
            next_item_id = numpy_array[next_item_index][5]
            next_item_qs = TestItems.objects.get(id=next_item_id)
            next_item = ItemsPartSerializer(next_item_qs)
        else:
            next_item = ItemsPartSerializer({})

        # 测定学生最新能力值
        after_theta = estimator.estimate(items=numpy_array,
                                         administered_items=mapped_list,
                                         response_vector=judge_list,
                                         est_theta=pre_theta)
        after_theta = round(after_theta, 8)
        req.data['process_ability'] = after_theta

        # 结束判断，依据最大标准误差<=0.2时（即累计信息量>=25）或做的题目达到40题时允许结束客观题部分
        ad_items_ndarray = used_items_ndarry(numpy_array, item_id_list)
        can_stop = stopper.stop(administered_items=ad_items_ndarray, theta=after_theta)
        testsetting_id = test_info.test_setting.id
        test_setting = TestSetting.objects.get(id=testsetting_id)
        object_total = test_setting.choice_total + test_setting.judge_total
        subject_total = test_setting.glossary_total + test_setting.saqs_total + test_setting.discuss_total
        if (len(used_obj_items) >= object_total):
            can_stop = True
        test_will_finish = False
        test_over = False
        if (len(used_obj_items) == object_total - 1 and subject_total == 0):
            test_will_finish = True

        update_item_difficulty(req.data)

        # 测试过程中用户最新能力值记录保存，存于测试记录表中
        test_info.newest_ability = round(after_theta, 8)
        if can_stop:
            test_info.finish_object_test = True
            if subject_total == 0:
                test_over = True
        test_info.save()

        # 测试做题记录保存
        record_test = ObjTestProcessSerializer(data=req.data)
        if record_test.is_valid(raise_exception=True):
            record_test.save()
            if (next_item):
                return Response(
                    {
                        'info': record_test.data,
                        'next_item': next_item.data,
                        'finishObjTest': can_stop,
                        'testWillFinish': test_will_finish,
                        'testAllFinish': test_over
                    }, status.HTTP_201_CREATED)

        return Response(record_test.errors, status.HTTP_400_BAD_REQUEST)


class InitTestProcessView(APIView):
    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['item_id', 'answer', 'test_id'],
        properties={
            'item_id': openapi.Schema(type=openapi.TYPE_NUMBER),
            'answer': openapi.Schema(type=openapi.TYPE_STRING),
            'test_id': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    ),
                         responses={
                             400:
                             'Bad Request',
                             201:
                             openapi.Response(description='OK',
                                              examples={
                                                  'application/json': {
                                                      'init_finished':
                                                      openapi.TYPE_BOOLEAN,
                                                      'init_ability': openapi.TYPE_NUMBER,
                                                  }
                                              }),
                         },
                         operation_summary='能力评估测试：提交客观题答案，并获取下一题')
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
        record_init_test = InitTestProcessSerializer(data=req.data)
        if record_init_test.is_valid(raise_exception=True):
            record_init_test.save()

        update_item_difficulty(req.data)

        init_tested_items = InitTestProcess.objects.filter(
            test_id=req.data['test_id']).values('id', 'test_id', 'item_id', 'judge')
        if (len(init_tested_items) == 5):
            true_count = 0
            for init_tested_item in init_tested_items:
                if init_tested_item['judge'] == True:
                    true_count += 1
            if (true_count == 0 or true_count == 5):
                init_ability_log = math.log((true_count + 0.5) / (5.5 - true_count))
            else:
                init_ability_log = math.log(true_count / (5 - true_count))
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
            choice_items = TestItems.objects.filter(type=1).values()
            # 选择题由易到难排序后
            sort_choice_items = sorted(choice_items, key=lambda x: x['difficulty'])

            init_used_items = []
            for init_tested_item in init_tested_items:
                item_id = init_tested_item['item_id']
                item = TestItems.objects.get(id=item_id)
                init_used_items.append({
                    'item_id': item_id,
                    'item_difficulty': item.difficulty,
                    'item_judge': init_tested_item['judge']
                })
            used_items_list = separate_dict('item_id', init_used_items)
            if init_used_items[-1]['item_judge']:  # 最新的一题做对
                item_id = init_used_items[-1]['item_id']
                difficulty = init_used_items[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sort_choice_items.index(item[0])
                if index + 11 > len(sort_choice_items):
                    index_list = range(index + 1, len(sort_choice_items))
                else:
                    index_list = range(index + 1, index + 11)
                init_next_item = None
                while True:
                    random_index = choice(index_list)
                    if (sort_choice_items[random_index]['difficulty'] - difficulty <=
                            0.5) and (sort_choice_items[random_index]['id']
                                      not in used_items_list):
                        init_next_item = sort_choice_items[random_index]
                        init_next_item_qs = TestItems.objects.get(
                            id=sort_choice_items[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_next_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_201_CREATED)
            else:  # 最新一题做错
                item_id = init_used_items[-1]['item_id']
                difficulty = init_used_items[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sort_choice_items.index(item[0])
                if index - 11 < 0:
                    index_list = range(0, index - 1)
                else:
                    index_list = range(index - 11, index - 1)
                init_next_item = None
                while True:
                    random_index = choice(index_list)
                    if (difficulty - sort_choice_items[random_index]['difficulty'] <=
                            0.5) and (sort_choice_items[random_index]['id']
                                      not in used_items_list):
                        init_next_item_qs = TestItems.objects.get(
                            id=sort_choice_items[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_next_item_qs)
                        break

                return Response({'next_item': init_next_item.data},
                                status.HTTP_201_CREATED)

    test_id = openapi.Parameter('test_id',
                                required=True,
                                in_=openapi.IN_QUERY,
                                description='考试记录Id',
                                type=openapi.TYPE_NUMBER)

    @swagger_auto_schema(manual_parameters=[test_id],
                         responses={
                             200:
                             openapi.Response(
                                 description='OK',
                                 examples={'application/json': {
                                     'next_item': {},
                                 }}),
                         },
                         operation_summary='能力评估测试：获取客观题题目(resume时调用)')
    #未完成初始能力测试，需要继续完成时调用此get请求，只返回相应题目
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
        init_tested_items = InitTestProcess.objects.filter(test_id=test_id).values(
            'id', 'test_id', 'item_id', 'judge')
        # 所有选择题
        choice_items = TestItems.objects.filter(type=1).values()
        # 选择题由易到难排序后
        sort_choice_items = sorted(choice_items, key=lambda x: x['difficulty'])
        init_used_items = []
        for init_tested_item in init_tested_items:
            item_id = init_tested_item['item_id']
            item = TestItems.objects.get(id=item_id)
            init_used_items.append({
                'item_id': item_id,
                'item_difficulty': item.difficulty,
                'item_judge': init_tested_item['judge']
            })
        if (not init_used_items):
            index_list = range(
                int(len(sort_choice_items) / 2) - 5,
                int(len(sort_choice_items) / 2) + 5)
            random_index = choice(index_list)
            first_item_qs = TestItems.objects.get(
                id=sort_choice_items[random_index]['id'])
            first_item = ItemsPartSerializer(first_item_qs)
            return Response({'next_item': first_item.data}, status.HTTP_200_OK)
        else:
            used_items_list = separate_dict('item_id', init_used_items)
            if init_used_items[-1]['item_judge']:  # 最新的一题做对
                item_id = init_used_items[-1]['item_id']
                difficulty = init_used_items[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sort_choice_items.index(item[0])
                if index + 11 > len(sort_choice_items):
                    index_list = range(index + 1, len(sort_choice_items))
                else:
                    index_list = range(index + 1, index + 11)
                init_next_item = None
                while True:
                    random_index = choice(index_list)
                    if (sort_choice_items[random_index]['difficulty'] - difficulty <=
                            0.5) and (sort_choice_items[random_index]['id']
                                      not in used_items_list):
                        init_next_item = sort_choice_items[random_index]
                        init_next_item_qs = TestItems.objects.get(
                            id=sort_choice_items[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_next_item_qs)
                        break
                return Response({'next_item': init_next_item.data}, status.HTTP_200_OK)
            else:  # 最新一题做错
                item_id = init_used_items[-1]['item_id']
                difficulty = init_used_items[-1]['item_difficulty']
                item = TestItems.objects.filter(id=item_id).values()
                index = sort_choice_items.index(item[0])
                if index - 11 < 0:
                    index_list = range(0, index - 1)
                else:
                    index_list = range(index - 11, index - 1)
                init_next_item = None
                while True:
                    random_index = choice(index_list)
                    if (difficulty - sort_choice_items[random_index]['difficulty'] <=
                            0.5) and (sort_choice_items[random_index]['id']
                                      not in used_items_list):
                        init_next_item_qs = TestItems.objects.get(
                            id=sort_choice_items[random_index]['id'])
                        init_next_item = ItemsPartSerializer(init_next_item_qs)
                        break
                return Response({'next_item': init_next_item.data}, status.HTTP_200_OK)


class TestContinueView(APIView):
    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['unfinished_test_id'],
        properties={
            'unfinished_test_id': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    ),
                         responses={
                             400:
                             'Bad Request',
                             200:
                             openapi.Response(description='OK',
                                              examples={
                                                  'application/json': {
                                                      'next_item': {},
                                                      'testWillFinish':
                                                      openapi.TYPE_BOOLEAN
                                                  }
                                              }),
                         },
                         operation_summary='未完成的考试继续测试，获取题目')
    def post(self, req):
        user_id = decode_token(req)['user_id']
        user = MyUser.objects.get(id=user_id)
        unfinished_test_id = req.data['unfinished_test_id']
        finish_obj_test = TestInfo.objects.get(
            test_id=unfinished_test_id).finish_object_test
        if (user.init_ability):
            if finish_obj_test:
                used_sbj_items = get_used_sbj_items(req.data)
                test_will_finish = check_test_will_finish(unfinished_test_id)
                selected_item_id = select_sbj_item(used_sbj_items, unfinished_test_id)
                next_sbj_item = TestItems.objects.get(id=selected_item_id)
                next_item = ItemsPartSerializer(next_sbj_item)
                return Response(
                    {
                        'next_item': next_item.data,
                        'testWillFinish': test_will_finish
                    }, status.HTTP_200_OK)
            else:
                used_obj_items = get_used_obj_items(req.data)
                numpy_array = switch_items_numpy(used_obj_items, 'object')
                item_id_list = separate_dict('item_id', used_obj_items)
                mapped_list = index_map(numpy_array, item_id_list)

                testId = req.data['unfinished_test_id']
                test_info = TestInfo.objects.get(test_id=testId)
                pre_theta = test_info.newest_ability
                selector = MaxInfoSelector()
                first_item_index = selector.select(items=numpy_array,
                                                   administered_items=mapped_list,
                                                   est_theta=pre_theta)
                first_item_id = numpy_array[first_item_index][5]
                first_item = TestItems.objects.get(id=first_item_id)

                testsetting_id = test_info.test_setting.id
                test_setting = TestSetting.objects.get(id=testsetting_id)
                object_total = test_setting.choice_total + test_setting.judge_total
                subject_total = test_setting.glossary_total + test_setting.saqs_total + test_setting.discuss_total
                test_will_finish = False
                if (len(used_obj_items) == object_total - 1 and subject_total == 0):
                    test_will_finish = True

                next_obj_item = ItemsPartSerializer(first_item)
                return Response(
                    {
                        'next_item': next_obj_item.data,
                        'testWillFinish': test_will_finish
                    }, status.HTTP_200_OK)
        else:
            return Response({
                'init_finished': False,
            }, status.HTTP_200_OK)


class SubjectTestProcessView(APIView):
    test_id = openapi.Parameter('test_id',
                                required=True,
                                in_=openapi.IN_QUERY,
                                description='考试记录Id',
                                type=openapi.TYPE_NUMBER)

    @swagger_auto_schema(manual_parameters=[test_id],
                         responses={
                             200:
                             openapi.Response(description='OK',
                                              examples={
                                                  'application/json': {
                                                      'next_item': {},
                                                      'testWillFinish':
                                                      openapi.TYPE_BOOLEAN
                                                  }
                                              }),
                         },
                         operation_summary='正式测试时，客观题完成后获取第一道主观题')
    def get(self, req):
        test_id = int(req.GET.get('test_id'))
        test_info = TestInfo.objects.get(test_id=test_id)
        test_will_finish = False
        testsetting_id = test_info.test_setting.id
        test_setting = TestSetting.objects.get(id=testsetting_id)
        subject_total = test_setting.glossary_total + test_setting.saqs_total + test_setting.discuss_total
        if subject_total <= 1:
            test_will_finish = True
        else:
            test_will_finish = False
        sbj_processes = SubjectTestProcess.objects.filter(test_id=test_id)
        if (test_info.finish_object_test and not sbj_processes):
            selected_item_id = select_sbj_item({}, test_id)
            next_sbj_item = TestItems.objects.get(id=selected_item_id)
            next_item = ItemsPartSerializer(next_sbj_item)
            return Response(
                {
                    'next_item': next_item.data,
                    'testWillFinish': test_will_finish
                }, status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['item_id', 'answer', 'test_id'],
        properties={
            'item_id': openapi.Schema(type=openapi.TYPE_NUMBER),
            'answer': openapi.Schema(type=openapi.TYPE_STRING),
            'test_id': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
    ),
                         responses={
                             400:
                             'Bad Request',
                             201:
                             openapi.Response(description='OK',
                                              examples={
                                                  'application/json': {
                                                      'info': {},
                                                      'next_item': {},
                                                      'testWillFinish':
                                                      openapi.TYPE_BOOLEAN,
                                                      'testAllFinish':
                                                      openapi.TYPE_BOOLEAN
                                                  }
                                              }),
                         },
                         operation_summary='提交主观题答案，并获取下一题')
    def post(self, req):
        user_id = decode_token(req)['user_id']
        req.data['user_id'] = user_id
        test_id = req.data.get('test_id')

        test_will_finish = check_test_will_finish(test_id)

        used_sbj_items = get_used_sbj_items(req.data)
        selected_item_id = select_sbj_item(used_sbj_items, test_id)
        if selected_item_id:
            next_sbj_item = TestItems.objects.get(id=selected_item_id)
            test_over = False
            next_item = ItemsPartSerializer(next_sbj_item)
        else:
            next_item = ItemsPartSerializer({})
            test_over = True
        # 测试做题记录保存
        record_test = SbjTestProcessSerializer(data=req.data)
        if record_test.is_valid(raise_exception=True):
            record_test.save()
            return Response(
                {
                    'info': record_test.data,
                    'next_item': next_item.data,
                    'testWillFinish': test_will_finish,
                    'testAllFinish': test_over
                }, status.HTTP_201_CREATED)
        return Response(record_test.errors, status.HTTP_400_BAD_REQUEST)