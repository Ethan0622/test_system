from django.urls import path

from . import views

urlpatterns = [
    path('test_setting/', views.TestSettingView.as_view()),
    path('test_info/', views.TestInfoView.as_view()),
    path('test_info_detail/<int:pk>/', views.TestInfoDetailView.as_view()),
    path('object_test_process/', views.ObjectTestProcessView.as_view()),
    path('subject_test_process/', views.SubjectTestProcessView.as_view()),
    path('init_test_process/', views.InitTestProcessView.as_view()),
    path('test_finish/<int:pk>/', views.TestFinishView.as_view()),
    path('test_continue/', views.TestContinueView.as_view())
]