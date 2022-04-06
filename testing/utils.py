from re import S
import numpy, math
from random import choice
from .models import SubjectTestProcess, TestInfo, ObjectTestProcess, InitTestProcess, TestSetting
from itembank.models import TestItems, ItemType
from .serializers import TestInfoSerializer, ObjTestProcessSerializer, ItemInfoSerializer
from itembank.serializers import ItemTypeSerializer


# 二分查找算法
def binary_search(sorted_sequence, target):
    left = 0
    right = len(sorted_sequence) - 1
    while (left <= right):
        midpoint = (left + right) // 2
        current_item = sorted_sequence[midpoint]
        if current_item['difficulty'] == target:
            return midpoint
        elif target < current_item['difficulty']:
            right = midpoint - 1
        else:
            left = midpoint + 1
    return None


# 将题目信息列表变成numpy数组，可以根据题目类型及题目对应知识点id挑选特定题目
# usedItems和type必填，type可取值范围['subject', 'object', 1, 2, 3, 4, 5]
def switch_items_numpy(usedItems, type, knowledge=None):
    object_id_qs = ItemType.objects.filter(is_subject=False).values('id')
    subject_id_qs = ItemType.objects.filter(is_subject=True).values('id')
    object_id = [x['id'] for x in object_id_qs]
    subject_id = [x['id'] for x in subject_id_qs]
    if knowledge:
        if type == 'subject':
            items_qs = TestItems.objects.filter(type__in=subject_id,
                                                knowledge_id=knowledge)
        elif type == 'object':
            items_qs = TestItems.objects.filter(type__in=object_id,
                                                knowledge_id=knowledge)
        else:
            items_qs = TestItems.objects.filter(type=type, knowledge_id=knowledge)
    else:
        if type == 'subject':
            items_qs = TestItems.objects.filter(type__in=subject_id)
        elif type == 'object':
            items_qs = TestItems.objects.filter(type__in=object_id)
        else:
            items_qs = TestItems.objects.filter(type=type)
    items = ItemInfoSerializer(items_qs, many=True)

    numpy_list = []
    for item in items.data:
        numpy_list.append([
            item["discrimination"], item["difficulty"], item["guessing"], 1,
            item['exposure'], item['id']
        ])
    for item in usedItems:
        item_id = item.get('item_id')
        item_info = TestItems.objects.get(id=item_id)
        numpy_list.append([
            item_info.discrimination, item_info.difficulty, item_info.guessing, 1,
            item_info.exposure, item_id
        ])
    # 嵌套列表去重且元素间顺序不变（因为题目列表中不能有重复题目，所以题目列表 = 选题范围 + 用户做过的题中不在选题范围里的题）
    numpy_list_duplicate = [list(t) for t in set(tuple(_) for _ in numpy_list)]
    numpy_list_duplicate.sort(key=numpy_list.index)
    numpy_array = numpy.array(numpy_list_duplicate)
    return numpy_array


# 将元组列表的所有元组中指定index的数据挑出来，组成一个列表；如果有一个元组的长度-1小于指定index，则会报错越界
def separate_tuple(index, tupleList):
    return_list = []
    for item in tupleList:
        if (index > len(item) - 1):
            return "maybe some tuple index out of range."
        return_list.append(item[index])
    return return_list


# 将字典列表的所有字典中指定key对应的value分离出来，组成一个列表；如果有一个字典中key不存在，则会报错没有键
def separate_dict(key, dictList):
    return_list = []
    for item in dictList:
        if (item.get(key) == None):
            return "maybe some dicts don't have the key."
        return_list.append(item.get(key))
    return return_list


# 获取难度系数为b的题目的id
def get_item_by_difficulty(b):
    all_items_qs = TestItems.objects.all()
    item_info = ItemInfoSerializer(all_items_qs, many=True)
    all_items = item_info.data
    items_list = list(all_items)
    sort_items_list = sorted(items_list, key=lambda x: x['difficulty'])
    index = binary_search(sort_items_list, b)
    if index:
        return sort_items_list[index]['id']
    else:
        return ("Error, the item do not exist.")


# 获取用户已经做过的客观题以及做题信息，返回一个字典列表，字典{客观题id，题目类型，题目对应知识点，正误}
def get_used_obj_items(reqData):
    used_obj_items = []
    # 不管是正常做题还是中途推出过继续做题，这之前的客观题做题记录都要查到并返回
    test_id = reqData.get('test_id') or reqData.get('unfinished_test_id')

    obj_items_qs = ObjectTestProcess.objects.filter(test_id=test_id)
    for obj_item in obj_items_qs:
        item = TestItems.objects.get(id=obj_item.item_id.id)
        used_obj_items.append({
            'item_id': item.id,
            'item_type': item.type.id,
            'item_knowledge': item.knowledge_id.id,
            'item_judge': obj_item.judge
        })
    # 如果是正常做题还要把这次提交的题目判断好正误，并添加到返回值中去
    if reqData.get('unfinished_test_id') == None:
        latest_item_id = reqData['item_id']
        latest_item = TestItems.objects.get(id=latest_item_id)
        judge = True if latest_item.correct == reqData['answer'] else False

        used_obj_items.append({
            'item_id': latest_item_id,
            'item_type': latest_item.type.id,
            'item_knowledge': latest_item.knowledge_id.id,
            'item_judge': judge
        })

    return used_obj_items


# 获取用户已经做过的主观题以及做题信息，返回一个字典列表，字典{客观题id，题目类型，题目对应知识点}
def get_used_sbj_items(reqData):
    used_sbj_items = []
    # 不管是正常做题还是中途推出过继续做题，这之前的主观题做题记录都要查到并返回
    test_id = reqData.get('test_id') or reqData.get('unfinished_test_id')
    sbj_items_qs = SubjectTestProcess.objects.filter(test_id=test_id)
    for sbj_item in sbj_items_qs:
        item = TestItems.objects.get(id=sbj_item.item_id.id)
        used_sbj_items.append({
            'item_id': item.id,
            'item_type': item.type.id,
            'item_knowledge': item.knowledge_id.id,
        })
    # 如果是正常做题，还要把本次提交的主观题添加到返回值中
    if reqData.get('unfinished_test_id') == None:
        latest_item_id = reqData['item_id']
        latest_item = TestItems.objects.get(id=latest_item_id)

        used_sbj_items.append({
            'item_id': latest_item_id,
            'item_type': latest_item.type.id,
            'item_knowledge': latest_item.knowledge_id.id,
        })

    return used_sbj_items


# 更新题目的难度系数b，前提是该题被用过5次以上，且并不是全对或全错
def update_item_difficulty(reqData):
    latest_item_id = reqData['item_id']
    object_test_list = ObjectTestProcess.objects.filter(
        item_id=latest_item_id).values('judge')
    init_test_list = InitTestProcess.objects.filter(
        item_id=latest_item_id).values('judge')
    item_tested_list = list(object_test_list) + list(init_test_list)

    latest_item = TestItems.objects.get(id=latest_item_id)
    judge = True if latest_item.correct == reqData['answer'] else False

    item_tested_list.append({'judge': judge})
    if len(item_tested_list) >= 5:
        true_item_tested_list = [x for x in item_tested_list if x['judge'] == True]
        len_all = len(item_tested_list)
        len_true = len(true_item_tested_list)
        if len_true == 0 or len_true == len_all:
            return False
        else:
            new_difficulty_log = math.log((len_all - len_true) / len_true)
            new_difficulty = round(new_difficulty_log, 8)
            latest_item.difficulty = new_difficulty
            latest_item.save()
            return True
    else:
        return False


# 返回一个列表：已经做过所有题目在numpy数组中的位置id，用于CAT计算
def index_map(ndarray, list):
    return_list = []
    ad_items_id_list = ndarray[:, 5]
    return_list = [numpy.argwhere(ad_items_id_list == x)[0][0] for x in list]
    return return_list


# 返回一个numpy数组：已经做过所有题目，用于计算是否可以终止测验
def used_items_ndarry(ndarray, list):
    return_list = []
    for id in list:
        for i in range(0, len(ndarray)):
            if id == ndarray[i][5]:
                return_list.append(ndarray[i])
                break
    return_ndarray = numpy.array(return_list)
    return return_ndarray


# 根据目前答题情况分析得出，需要返回的挑选的题目条件（何种类型、何种知识点）
def obj_select_range(dictList):
    knowledge_list = []
    Knowledge_count = {}
    type_list = []
    type_count = {}
    return_dict = {'type': 'object', 'knowledge_id': None}
    for item in dictList:
        knowledge_list.append(item.get('item_knowledge'))
        type_list.append(item.get('item_type'))
    for i in range(1, 3):
        type_count[i] = type_list.count(i)
    for i in range(1, 9):
        Knowledge_count[i] = knowledge_list.count(i)

    non_knowledge_list = [x[0] for x in Knowledge_count.items() if x[1] <= 1]
    if type_count[2] >= 10:
        return_dict['type'] = 1
    elif len(non_knowledge_list):  # 每个知识点客观题至少两题
        return_dict['knowledge_id'] = choice(non_knowledge_list)
    else:
        # 比较知识点错题量进行选题
        pass
    return return_dict


def select_sbj_item(dictList, testId):
    knowledge_list = []
    Knowledge_count = {}
    type_list = []
    type_count = {}
    test_info = TestInfo.objects.get(test_id=testId)
    testsetting_id = test_info.test_setting.id
    test_setting = TestSetting.objects.get(id=testsetting_id)
    for item in dictList:
        knowledge_list.append(item.get('item_knowledge'))
        type_list.append(item.get('item_type'))
    for i in range(3, 6):
        type_count[i] = type_list.count(i)
    for i in range(1, 9):
        Knowledge_count[i] = knowledge_list.count(i)
    non_knowledge_list = [x[0] for x in Knowledge_count.items() if x[1] <= 0]
    if type_count[3] < test_setting.glossary_total:
        # 选几道名词解释
        tested_id = [x['item_id'] for x in dictList if x['item_type'] == 3]
        mcjs = list(TestItems.objects.filter(type=3).values('id', 'type', 'knowledge_id'))
        un_tested_mcjs = [x for x in mcjs if x['id'] not in tested_id]
        return choice(un_tested_mcjs)['id']
    elif type_count[4] < test_setting.saqs_total:
        # 选几道简答题
        tested_id = [x['item_id'] for x in dictList if x['item_type'] == 4]
        jd = list(TestItems.objects.filter(type=4).values('id', 'type', 'knowledge_id'))
        un_tested_jd = [x for x in jd if x['id'] not in tested_id]
        return choice(un_tested_jd)['id']
    elif type_count[5] < test_setting.discuss_total:
        # 选几道论述题
        tested_id = [x['item_id'] for x in dictList if x['item_type'] == 5]
        ls = list(TestItems.objects.filter(type=5).values('id', 'type', 'knowledge_id'))
        un_tested_ls = [x for x in ls if x['id'] not in tested_id]
        return choice(un_tested_ls)['id']
    else:
        # 考试结束
        return None


# 更新题目的曝光系数
def update_item_exposure(id):
    used_count = len(ObjectTestProcess.objects.filter(item_id=id))
    tests_total = len(TestInfo.objects.all())
    exposure_rate = round(used_count / tests_total, 3)
    item = TestItems.objects.get(id=id)
    item.exposure = exposure_rate
    item.save()


# 验证本次考试所指定的各种题型的数量不超过题库中该题型的总题量
def validate_item_total(reqData):
    choice_total = reqData.get('choice_total', 0)
    judge_total = reqData.get('judge_total', 0)
    glossary_total = reqData.get('glossary_total', 0)
    saqs_total = reqData.get('saqs_total', 0)
    discuss_total = reqData.get('discuss_total', 0)

    key_list = [
        'choice_total', 'judge_total', 'glossary_total', 'saqs_total', 'discuss_total'
    ]

    total_list = [('choice_total', choice_total), ('judge_total', judge_total),
                  ('glossary_total', glossary_total), ('saqs_total', saqs_total),
                  ('discuss_total', discuss_total)]

    choice_sum = TestItems.objects.filter(type=1).count()
    judge_sum = TestItems.objects.filter(type=2).count()
    glossary_sum = TestItems.objects.filter(type=3).count()
    saqs_sum = TestItems.objects.filter(type=4).count()
    discuss_sum = TestItems.objects.filter(type=5).count()

    sum_list = [choice_sum, judge_sum, glossary_sum, saqs_sum, discuss_sum]

    filter_req_data = {}
    for key in key_list:
        filter_req_data[key] = reqData[key]
    testsetting_exist = TestSetting.objects.filter(**filter_req_data).values('id')
    if testsetting_exist:
        return testsetting_exist[0]['id']

    for i in range(0, 5):
        if (total_list[i][1] > sum_list[i]):
            return total_list[i][0]


def check_test_will_finish(test_id):
    test_info = TestInfo.objects.get(test_id=test_id)
    testsetting_id = test_info.test_setting.id
    test_setting = TestSetting.objects.get(id=testsetting_id)
    subject_total = test_setting.glossary_total + test_setting.saqs_total + test_setting.discuss_total
    if (subject_total <= 1):
        return True
    else:
        subject_record_count = SubjectTestProcess.objects.filter(test_id=test_id).count()
        if subject_record_count + 2 == subject_total:
            return True
        else:
            return False