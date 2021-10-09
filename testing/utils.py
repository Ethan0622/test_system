import numpy
from .models import TestInfo, ObjectTestProcess
from .serializers import TestInfoSerializer, ObjTestProcessSerializer, ItemInfoSerializer
from itembank.models import TestItems


# 二分查找算法
def binarysearch(sorted_sequence, target):
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


# 将数据变成numpy数组
def switchNumpy(data):
    numpyList = []
    for item in data:
        numpyList.append(
            [item["discrimination"], item["difficulty"], item["guessing"], 1])
    numpyArray = numpy.array(numpyList)
    return numpyArray


# 将元组每个元素中指定位置的数据挑出来，组成一个列表
def separateTuple(index, tupleList):
    returnList = []
    for item in tupleList:
        returnList.append(item[index])
    return returnList


# 获取难度系数为b的题目的id
def getItemBydifficulty(b):
    qs = TestItems.objects.all()
    itemInfo = ItemInfoSerializer(qs, many=True)
    allItems = itemInfo.data
    itemsList = list(allItems)
    sortList = sorted(itemsList, key=lambda x: x['difficulty'])
    index = binarysearch(sortList, b)
    if index:
        return sortList[index]['id']
    else:
        return ("Error, Can't find the item")


# 获取用户已经做过的题目以及做题信息，返回一个元组列表，元组（题目id， 题目类型， 正误）
def getUsedItems(reqData):
    usedItems = []
    test_id = reqData['test_id']
    latest_item_id = reqData['item_id']
    latest_item = TestItems.objects.filter(id=latest_item_id).values()
    if latest_item[0]['correct'] == reqData['answer']:
        judge = True
    else:
        judge = False
    ItemsQS = ObjectTestProcess.objects.filter(test_id=test_id)

    for i in ItemsQS:
        item_type = TestItems.objects.filter(
            id=i['item_id']).values()[0]['type']
        usedItems.append((i['item_id'], item_type, i['judge']))

    usedItems.append((latest_item_id, latest_item[0]['type'], judge))

    return usedItems


# 返回一个列表：已经做过所有题目在numpy数组中的位置id，用于cat计算
def indexMap(ndarry, list):
    tupleList = []
    returnList = []
    for id in list:
        item_difficulty = TestItems.objects.filter(
            id=id).values()[0]['difficulty']
        tupleList.append((id, item_difficulty))
    for item in tupleList:
        for i in range(0, len(ndarry)):
            if item[1] == ndarry[i][1]:
                returnList.append(i)
                break
    return returnList
