from django.urls import path

from . import views

urlpatterns = [
    path('test_info/', views.TestInfoView.as_view()),
    path('test_info_detail/<int:pk>/', views.TestInfoDetailView.as_view()),
    path('object_test_process/', views.TestProcessView.as_view())
]