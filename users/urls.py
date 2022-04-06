from django.urls import path
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    path('user_list/', views.userListView.as_view()),
    path('user_detail/<int:pk>/', views.userDetailView.as_view()),
    path('user_tests_list/', views.userTestsListView.as_view()),
    path('user_check_tests/', views.checkUserTestsView.as_view()),
    # path('user_login/', obtain_jwt_token)
    path('user_login/', views.userLoginJWTView.as_view())
]