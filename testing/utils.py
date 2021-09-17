import numpy
from .models import TestInfo, ObjectTestProcess
from .serializers import TestInfoSerializer, ObjTestProcessSerializer, ItemInfoSerializer
from itembank.models import TestItems


def binarysearch(sorted_sequence, target):
    left = 0
    right = len(sorted_sequence) - 1
    while (left <= right):
        midpoint = (left + right) // 2
        current_item = sorted_sequence[midpoint]
        if current_item['diffculty'] == target:
            return midpoint
        elif target < current_item['diffculty']:
            right = midpoint - 1
        else:
            left = midpoint + 1
    return None


def switchNumpy(data):
    numpyList = []
    for item in data:
        numpyList.append(
            [item["discrimination"], item["diffculty"], item["guessing"], 1])
    numpyArray = numpy.array(numpyList)
    return numpyArray


def separateTuple(index, tupleList):
    returnList = []
    for item in tupleList:
        returnList.append(item[index])
    return returnList


def getItemBydiffculty(b):
    qs = TestItems.objects.all()
    itemInfo = ItemInfoSerializer(qs, many=True)
    allItems = itemInfo.data
    itemsList = list(allItems)
    sortList = sorted(itemsList, key=lambda x: x['diffculty'])
    index = binarysearch(sortList, b)
    if index:
        return sortList[index]['id']
    else:
        return ("Error, Can't find the item")


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


def indexMap(ndarry, list):
    tupleList = []
    returnList = []
    for id in list:
        item_diffculty = TestItems.objects.filter(
            id=id).values()[0]['diffculty']
        tupleList.append((id, item_diffculty))
    for item in tupleList:
        for i in range(0, len(ndarry)):
            if item[1] == ndarry[i][1]:
                returnList.append(i)
                break
    return returnList
