import numpy, math
from random import choice
from .models import SubjectTestProcess, TestInfo, ObjectTestProcess, InitTestProcess
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
    objectIdQS = ItemType.objects.filter(is_subject=False).values('id')
    subjectIdQS = ItemType.objects.filter(is_subject=True).values('id')
    objectId = [x['id'] for x in objectIdQS]
    subjectId = [x['id'] for x in subjectIdQS]
    if knowledge:
        if type == 'subject':
            itemsQS = TestItems.objects.filter(type__in=subjectId, knowledge_id=knowledge)
        elif type == 'object':
            itemsQS = TestItems.objects.filter(type__in=objectId, knowledge_id=knowledge)
        else:
            itemsQS = TestItems.objects.filter(type=type, knowledge_id=knowledge)
    else:
        if type == 'subject':
            itemsQS = TestItems.objects.filter(type__in=subjectId)
        elif type == 'object':
            itemsQS = TestItems.objects.filter(type__in=objectId)
        else:
            itemsQS = TestItems.objects.filter(type=type)
    Items = ItemInfoSerializer(itemsQS, many=True)

    numpyList = []
    for item in Items.data:
        numpyList.append([
            item["discrimination"], item["difficulty"], item["guessing"], 1,
            item['exposure'], item['id']
        ])
    for item in usedItems:
        item_id = item.get('item_id')
        itemInfo = TestItems.objects.get(id=item_id)
        numpyList.append([
            itemInfo.discrimination, itemInfo.difficulty, itemInfo.guessing, 1,
            itemInfo.exposure, item_id
        ])
    # 嵌套列表去重且元素间顺序不变（因为题目列表中不能有重复题目，所以题目列表 = 选题范围 + 用户做过的题中不在选题范围里的题）
    numpyListDuplicate = [list(t) for t in set(tuple(_) for _ in numpyList)]
    numpyListDuplicate.sort(key=numpyList.index)
    numpyArray = numpy.array(numpyListDuplicate)
    return numpyArray


# 将元组列表的所有元组中指定index的数据挑出来，组成一个列表；如果有一个元组的长度-1小于指定index，则会报错越界
def separate_tuple(index, tupleList):
    returnList = []
    for item in tupleList:
        if (index > len(item) - 1):
            return "maybe some tuple index out of range."
        returnList.append(item[index])
    return returnList


# 将字典列表的所有字典中指定key对应的value分离出来，组成一个列表；如果有一个字典中key不存在，则会报错没有键
def separate_dict(key, dictList):
    returnList = []
    for item in dictList:
        if (item.get(key) == None):
            return "maybe some dicts don't have the key."
        returnList.append(item.get(key))
    return returnList


# 获取难度系数为b的题目的id
def get_item_by_difficulty(b):
    qs = TestItems.objects.all()
    itemInfo = ItemInfoSerializer(qs, many=True)
    allItems = itemInfo.data
    itemsList = list(allItems)
    sortList = sorted(itemsList, key=lambda x: x['difficulty'])
    index = binary_search(sortList, b)
    if index:
        return sortList[index]['id']
    else:
        return ("Error, the item do not exist.")


# 获取用户已经做过的客观题以及做题信息，返回一个字典列表，字典{客观题id，题目类型，题目对应知识点，正误}
def get_used_obj_items(reqData):
    usedObjItems = []
    # 不管是正常做题还是中途推出过继续做题，这之前的客观题做题记录都要查到并返回
    test_id = reqData.get('test_id') or reqData.get('unfinished_test_id')

    ItemsQS = ObjectTestProcess.objects.filter(test_id=test_id)
    for i in ItemsQS:
        item = TestItems.objects.get(id=i.item_id.id)
        usedObjItems.append({
            'item_id': item.id,
            'item_type': item.type.id,
            'item_knowledge': item.knowledge_id.id,
            'item_judge': i.judge
        })
    # 如果是正常做题还要把这次提交的题目判断好正误，并添加到返回值中去
    if reqData.get('unfinished_test_id') == None:
        latest_item_id = reqData['item_id']
        latest_item = TestItems.objects.get(id=latest_item_id)
        judge = True if latest_item.correct == reqData['answer'] else False

        usedObjItems.append({
            'item_id': latest_item_id,
            'item_type': latest_item.type.id,
            'item_knowledge': latest_item.knowledge_id.id,
            'item_judge': judge
        })

    return usedObjItems


# 获取用户已经做过的主观题以及做题信息，返回一个字典列表，字典{客观题id，题目类型，题目对应知识点}
def get_used_sbj_items(reqData):
    usedSbjItems = []
    # 不管是正常做题还是中途推出过继续做题，这之前的主观题做题记录都要查到并返回
    test_id = reqData.get('test_id') or reqData.get('unfinished_test_id')
    ItemsQS = SubjectTestProcess.objects.filter(test_id=test_id)
    for i in ItemsQS:
        item = TestItems.objects.get(id=i.item_id.id)
        usedSbjItems.append({
            'item_id': item.id,
            'item_type': item.type.id,
            'item_knowledge': item.knowledge_id.id,
        })
    # 如果是正常做题，还要把本次提交的主观题添加到返回值中
    if reqData.get('unfinished_test_id') == None:
        latest_item_id = reqData['item_id']
        latest_item = TestItems.objects.get(id=latest_item_id)

        usedSbjItems.append({
            'item_id': latest_item_id,
            'item_type': latest_item.type.id,
            'item_knowledge': latest_item.knowledge_id.id,
        })

    return usedSbjItems


# 更新题目的难度系数b，前提是该题被用过5次以上，且并不是全对或全错
def update_item_difficulty(reqData):
    latest_item_id = reqData['item_id']
    objectTestList = ObjectTestProcess.objects.filter(
        item_id=latest_item_id).values('judge')
    initTestList = InitTestProcess.objects.filter(item_id=latest_item_id).values('judge')
    itemTestedList = list(objectTestList) + list(initTestList)

    latest_item = TestItems.objects.get(id=latest_item_id)
    judge = True if latest_item.correct == reqData['answer'] else False

    itemTestedList.append({'judge': judge})
    if len(itemTestedList) >= 5:
        true_itemTestedList = [x for x in itemTestedList if x['judge'] == True]
        len_all = len(itemTestedList)
        len_true = len(true_itemTestedList)
        if len_true == 0 or len_true == len_all:
            return False
        else:
            newDifficultyLog = math.log((len_all - len_true) / len_true)
            newDifficulty = round(newDifficultyLog, 8)
            latest_item.difficulty = newDifficulty
            latest_item.save()
            return True
    else:
        return False


# 返回一个列表：已经做过所有题目在numpy数组中的位置id，用于CAT计算
def index_map(ndarray, list):
    returnList = []
    adItemsIdList = ndarray[:, 5]
    returnList = [numpy.argwhere(adItemsIdList == x)[0][0] for x in list]
    return returnList


# 返回一个numpy数组：已经做过所有题目，用于计算是否可以终止测验
def used_items_ndarry(ndarray, list):
    returnList = []
    for id in list:
        for i in range(0, len(ndarray)):
            if id == ndarray[i][5]:
                returnList.append(ndarray[i])
                break
    returnNdarray = numpy.array(returnList)
    return returnNdarray


# 根据目前答题情况分析得出，需要返回的挑选的题目条件（何种类型、何种知识点）
def obj_select_range(dictList):
    knowledgeList = []
    KnowledgeCount = {}
    typeList = []
    typeCount = {}
    returnDict = {'type': 'object', 'knowledge_id': None}
    for item in dictList:
        knowledgeList.append(item.get('item_knowledge'))
        typeList.append(item.get('item_type'))
    for i in range(1, 3):
        typeCount[i] = typeList.count(i)
    for i in range(1, 9):
        KnowledgeCount[i] = knowledgeList.count(i)

    non_knowledgeList = [x[0] for x in KnowledgeCount.items() if x[1] <= 1]
    if typeCount[2] >= 10:
        returnDict['type'] = 1
    elif len(non_knowledgeList):  # 每个知识点客观题至少两题
        returnDict['knowledge_id'] = choice(non_knowledgeList)
    else:
        # 比较知识点错题量进行选题
        pass
    return returnDict


def select_sbj_item(dictList):
    knowledgeList = []
    KnowledgeCount = {}
    typeList = []
    typeCount = {}
    for item in dictList:
        knowledgeList.append(item.get('item_knowledge'))
        typeList.append(item.get('item_type'))
    for i in range(3, 6):
        typeCount[i] = typeList.count(i)
    for i in range(1, 9):
        KnowledgeCount[i] = knowledgeList.count(i)
    non_knowledgeList = [x[0] for x in KnowledgeCount.items() if x[1] <= 0]
    if typeCount[3] < 4:
        # 选4道名词解释
        testedId = [x['item_id'] for x in dictList if x['item_type'] == 3]
        mcjs = list(TestItems.objects.filter(type=3).values('id', 'type', 'knowledge_id'))
        unTestedmcjs = [x for x in mcjs if x['id'] not in testedId]
        return choice(unTestedmcjs)['id']
    elif typeCount[4] < 2:
        # 选2道简答题
        testedId = [x['item_id'] for x in dictList if x['item_type'] == 4]
        jd = list(TestItems.objects.filter(type=4).values('id', 'type', 'knowledge_id'))
        unTestedjd = [x for x in jd if x['id'] not in testedId]
        return choice(unTestedjd)['id']
    elif typeCount[5] < 1:
        # 选1道论述题
        testedId = [x['item_id'] for x in dictList if x['item_type'] == 5]
        ls = list(TestItems.objects.filter(type=5).values('id', 'type', 'knowledge_id'))
        unTestedls = [x for x in ls if x['id'] not in testedId]
        return choice(unTestedls)['id']
    else:
        # 考试结束
        return None


# 更新题目的曝光系数
def update_item_exposure(id):
    usedCount = len(ObjectTestProcess.objects.filter(item_id=id))
    testsTotal = len(TestInfo.objects.all())
    exposureRate = round(usedCount / testsTotal, 3)
    item = TestItems.objects.get(id=id)
    item.exposure = exposureRate
    item.save()