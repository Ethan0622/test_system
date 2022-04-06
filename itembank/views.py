import xlrd
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from users.models import MyUser
from .models import TestItems, ItemType, TestPaper, TestPaperInfo
from .serializers import ItemsAllSerializer, TestPaperInfoSerializer, TestPaperSerializer
from testing.serializers import ItemsPartSerializer
from users.utils import decode_token


class itemListView(APIView):
    @swagger_auto_schema(responses={200: 'OK'}, operation_summary='获取每种题型的总题量')
    # 获取每种题型的总题量
    def get(self, req):
        choice_sum = TestItems.objects.filter(type=1).count()
        judge_sum = TestItems.objects.filter(type=2).count()
        glossary_sum = TestItems.objects.filter(type=3).count()
        saqs_sum = TestItems.objects.filter(type=4).count()
        discuss_sum = TestItems.objects.filter(type=5).count()
        return Response(
            {
                'choice_sum': choice_sum,
                'judge_sum': judge_sum,
                'glossary_sum': glossary_sum,
                'saqs_sum': saqs_sum,
                'discuss_sum': discuss_sum
            }, status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        description='如果是单项选择题则四个选项都需要有',
        required=[
            'type', 'knowledge_id', 'content', 'correct', 'difficulty', 'option_A',
            'option_B', 'option_C', 'option_D'
        ],
        properties={
            'type':
            openapi.Schema(type=openapi.TYPE_NUMBER, enum=[1, 2, 3, 4, 5]),
            'knowledge_id':
            openapi.Schema(type=openapi.TYPE_NUMBER, enum=[1, 2, 3, 4, 5, 6, 7, 8]),
            'content':
            openapi.Schema(type=openapi.TYPE_STRING),
            'correct':
            openapi.Schema(type=openapi.TYPE_STRING),
            'difficulty':
            openapi.Schema(type=openapi.TYPE_NUMBER),
            'option_A':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_B':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_C':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_D':
            openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             200: ItemsAllSerializer
                         },
                         operation_summary='新增一道题目')
    def post(self, req):
        create_item = ItemsAllSerializer(data=req.data)
        if create_item.is_valid(raise_exception=True):
            create_item.save()
            return Response(create_item.data, status.HTTP_201_CREATED)
        return Response(create_item.errors, status.HTTP_400_BAD_REQUEST)


class itemListTypeView(APIView):
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: ItemsAllSerializer
    },
                         operation_summary='查看指定类型的所有题目')
    def get(self, req, pk):
        try:
            type_exist = ItemType.objects.get(id=pk)
        except ItemType.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        type_items_qs = TestItems.objects.filter(type=pk)
        type_items = ItemsAllSerializer(instance=type_items_qs, many=True)
        return Response(type_items.data, status.HTTP_200_OK)


class itemInfoDetailView(APIView):
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: ItemsAllSerializer
    },
                         operation_summary='查看一道题的全部信息')
    def get(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        get_item = ItemsAllSerializer(instance=item)
        return Response(get_item.data, status.HTTP_200_OK)

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        description='如果是单项选择题则四个选项都需要有',
        required=[
            'type', 'knowledge_id', 'content', 'correct', 'difficulty', 'option_A',
            'option_B', 'option_C', 'option_D'
        ],
        properties={
            'type':
            openapi.Schema(type=openapi.TYPE_NUMBER, enum=[1, 2, 3, 4, 5]),
            'knowledge_id':
            openapi.Schema(type=openapi.TYPE_NUMBER, enum=[1, 2, 3, 4, 5, 6, 7, 8]),
            'content':
            openapi.Schema(type=openapi.TYPE_STRING),
            'correct':
            openapi.Schema(type=openapi.TYPE_STRING),
            'difficulty':
            openapi.Schema(type=openapi.TYPE_NUMBER),
            'option_A':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_B':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_C':
            openapi.Schema(type=openapi.TYPE_STRING),
            'option_D':
            openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
                         responses={
                             400: 'Bad Request',
                             404: 'Not Found',
                             200: ItemsAllSerializer
                         },
                         operation_summary='修改一道题目的信息')
    def put(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        update_item = ItemsAllSerializer(instance=item, data=req.data, partial=True)
        if update_item.is_valid(raise_exception=True):
            update_item.save()
            return Response(update_item.data, status.HTTP_200_OK)
        return Response(update_item.errors, status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={
        404: 'Not Found',
        204: 'No Content'
    },
                         operation_summary='删除一道题')
    def delete(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class itemDetailView(APIView):
    @swagger_auto_schema(responses={
        404: 'Not Found',
        200: ItemsPartSerializer
    },
                         operation_summary='查看一道题的部分信息（只提供做题所需的内容）')
    def get(self, req, pk):
        try:
            item = TestItems.objects.get(id=pk)
        except TestItems.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        get_item = ItemsPartSerializer(instance=item)
        return Response(get_item.data, status.HTTP_200_OK)


class itemsFileUploadView(APIView):
    @swagger_auto_schema(operation_summary='本接口涉及文件传输，开发人员偷懒不想写了，请自行查看代码')
    def post(self, req):
        '''通过上传文件批量添加试题'''
        upload_file = req.FILES['file']
        wb = xlrd.open_workbook(filename=None, file_contents=upload_file.read())
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
        create_errors = []
        for i in range(1, rows):
            row = table.row_values(i)
            if '' in row[:5]:
                return Response({'error': '部分题目的必填项未填写，请检查'}, status.HTTP_400_BAD_REQUEST)
            elif row[0] == 1 and '' in row[-4:]:
                return Response({'error': '部分选择题的选项未填写，请检查'}, status.HTTP_400_BAD_REQUEST)
            elif row[0] != 1:
                row = row[:5]
            item_info = dict(zip(item_key, row))
            create_item = ItemsAllSerializer(data=item_info)
            if create_item.is_valid():
                pass
            else:
                if 'content' in create_item.errors.keys():
                    create_errors.append("题目重复，提交的excel题目中第{}题在题库中已有".format(str(i)))
                else:
                    create_errors.append("将题目插入数据库时出错，错误原因：{}".format(
                        list(create_item.errors.values())[0][0]))
        if len(create_errors):
            return Response({'errors': create_errors}, status.HTTP_400_BAD_REQUEST)
        else:
            for i in range(1, rows):
                row = table.row_values(i)
                row[1] = round(row[1], 8)  # 保证难度系数保留8位小数（前提：如果超出8位）
                row = row[:5] if row[0] != 1 else row  # 只有选择题有选项
                row[4] = int(
                    row[4]) if row[0] == 2 else row[4]  # 保证判断题的正确答案是整数形式的字符串，不能有小数点
                item_info = dict(zip(item_key, row))
                create_item = ItemsAllSerializer(data=item_info)
                create_item.is_valid()
                create_item.save()
            return Response({'msg': '所有题目保存完成'}, status=status.HTTP_200_OK)


class TestPaperListView(APIView):
    permission_classes = (IsAdminUser, )

    @swagger_auto_schema(operation_summary='创建一份试卷；注意：目前接口不可用', deprecated=True)
    def post(self, req):
        user_id = decode_token(req)['user_id']
        req_data = req.data
        req_data['paper_teacher'] = user_id
        create_paper = TestPaperInfoSerializer(data=req.data)
        if create_paper.is_valid(raise_exception=True):
            create_paper.save()
            return Response(create_paper.data, status.HTTP_201_CREATED)
        return Response(create_paper.errors, status.HTTP_400_BAD_REQUEST)


class TestPaperDetailView(APIView):
    permission_classes = (IsAdminUser, )

    @swagger_auto_schema(operation_summary='往试卷中添加试题；注意：目前接口不可用', deprecated=True)
    def post(self, req, pk):
        try:
            paper = TestPaperInfo.objects.get(id=pk)
        except TestPaperInfo.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        req_data = req.data
        req_data['paper_id'] = paper.id
        for item_id in req.data['item_id']:
            try:
                item = TestItems.objects.get(id=item_id)
            except TestItems.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            req_data['item_id'] = item.id
            add_item_into_paper = TestPaperSerializer(data=req_data)
            if add_item_into_paper.is_valid(raise_exception=True):
                add_item_into_paper.save()
        return Response({'msg': '所选题目已添加到试卷中'}, status.HTTP_201_CREATED)
