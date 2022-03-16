from django.urls import path

from . import views

urlpatterns = [
    path('item_list/', views.itemListView.as_view()),
    path('item_type_list/<int:pk>/', views.itemListTypeView.as_view()),
    path('item_detail/<int:pk>/', views.itemDetailView.as_view()),
    path('item_info/<int:pk>/', views.itemInfoDetailView.as_view()),
    path('upload_item_files/',views.itemsFileUploadView.as_view()),
    path('test_paper/', views.TestPaperListView.as_view()),
    path('test_paper/<int:pk>/', views.TestPaperDetailView.as_view())
]