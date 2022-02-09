from django.urls import path

from . import views

urlpatterns = [
    path('class_list/', views.classListView.as_view()),
    path('class_info/', views.classInfoView.as_view()),
    path('class_student/<int:pk>/', views.classStudentView.as_view()),
    path('class_detail/<int:pk>/', views.classDetailView.as_view()),
    path('class_test/<int:pk>/', views.classTestView.as_view())
]