import xlrd
from rest_framework import status
from rest_framework import response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser

from users.models import MyUser
from .models import TestItems, ItemType, TestPaper, TestPaperInfo
from .serializers import ItemsAllSerializer, ItemsPartSerializer, TestPaperInfoSerializer, TestPaperSerializer

from users.utils import decode_token


class itemListView(APIView):
    # 新增试题
    def post(self, req):
        createItem = ItemsAllSerializer(data=req.data)
        if createItem.is_valid(raise_exception=True):
            createItem.save()
            return Response(createItem.data, status.HTTP_201_CREATED)
        return Response(createItem.errors, status.HTTP_400_BAD_REQUEST)


class itemListTypeView(APIView):
    # 查看指定类型的题目
    def get(self, req, pk):
        try:
            typeExist = ItemType.objects.get(id=pk)
        except ItemType.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        typeItemQS = TestItems.objects.filter(type=pk)
        typeItemList = ItemsAllSerializer(instance=typeItemQS, many=True)
        return Response(typeItemList.data, status.HTTP_200_OK)


class itemInfoDetailView(APIView):
    #获取、修改、删除特定id的题目，使用全部题目信息的序列化器（供教师用）

    def get(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        getItem = ItemsAllSerializer(instance=item)
        return Response(getItem.data, status.HTTP_200_OK)

    def put(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        updateItem = ItemsAllSerializer(instance=item, data=req.data, partial=True)
        if updateItem.is_valid(raise_exception=True):
            updateItem.save()
            return Response(updateItem.data, status.HTTP_200_OK)
        return Response(updateItem.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class itemDetailView(APIView):
    # 获取指定id试题，只提供主要题目信息（做题用）
    def get(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        getItem = ItemsPartSerializer(instance=item)
        return Response(getItem.data, status.HTTP_200_OK)


class itemsFileUploadView(APIView):
    def post(self, req):
        uploadFile = req.FILES['file']
        wb = xlrd.open_workbook(filename=None, file_contents=uploadFile.read())
        table = wb.sheets()[0]
        rows = table.nrows
        cols = table.ncols
        if cols != 9:
            return Response({'error': '请使用本网站所提供的excel模板进行提交'},
                            status.HTTP_400_BAD_REQUEST)
        item_key = [
            'type', "difficulty", "knowledge_id", "content", "correct", "option_A",
            "option_B", "option_C", "option_D"
        ]
        createErrors = []
        for i in range(1, rows):
            row = table.row_values(i)
            if '' in row[:5]:
                return Response({'error': '部分题目的必填项未填写，请检查'}, status.HTTP_400_BAD_REQUEST)
            elif row[0] == 1 and '' in row[-4:]:
                return Response({'error': '部分选择题的选项未填写，请检查'}, status.HTTP_400_BAD_REQUEST)
            elif row[0] != 1:
                row = row[:5]
            itemInfo = dict(zip(item_key, row))
            createItem = ItemsAllSerializer(data=itemInfo)
            if createItem.is_valid():
                pass
            else:
                if 'content' in createItem.errors.keys():
                    createErrors.append("题目重复，提交的excel题目中第{}题在题库中已有".format(str(i)))
                else:
                    createErrors.append("将题目插入数据库时出错，错误原因：{}".format(
                        list(createItem.errors.values())[0][0]))
        if len(createErrors):
            return Response({'errors': createErrors}, status.HTTP_400_BAD_REQUEST)
        else:
            for i in range(1, rows):
                row = table.row_values(i)
                row = row[:5] if row[0] != 1 else row
                itemInfo = dict(zip(item_key, row))
                createItem = ItemsAllSerializer(data=itemInfo)
                createItem.is_valid()
                createItem.save()
            return Response({'msg': '所有题目保存完成'}, status=status.HTTP_200_OK)


class TestPaperListView(APIView):
    permission_classes = (IsAdminUser, )

    # 创建一份试卷
    def post(self, req):
        userId = decode_token(req)['user_id']
        reqData = req.data
        reqData['paper_teacher'] = userId
        createPaper = TestPaperInfoSerializer(data=req.data)
        if createPaper.is_valid(raise_exception=True):
            createPaper.save()
            return Response(createPaper.data, status.HTTP_201_CREATED)
        return Response(createPaper.errors, status.HTTP_400_BAD_REQUEST)


class TestPaperDetailView(APIView):
    permission_classes = (IsAdminUser, )

    # 往试卷中添加试题
    def post(self, req, pk):
        try:
            paper = TestPaperInfo.objects.get(id=pk)
        except TestPaperInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        reqData = req.data
        reqData['paper_id'] = paper.id
        for itemId in req.data['item_id']:
            try:
                item = TestItems.objects.get(id=itemId)
            except TestItems.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            reqData['item_id'] = item.id
            addItemIntoPaper = TestPaperSerializer(data=reqData)
            if addItemIntoPaper.is_valid(raise_exception=True):
                addItemIntoPaper.save()
        return Response({'msg': '所选题目已添加到试卷中'}, status.HTTP_201_CREATED)
