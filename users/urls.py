from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    path('user_list/', views.userListView.as_view()),
    path('user_detail/<int:pk>/', views.userDetailView.as_view()),

    path('user_login/', obtain_jwt_token)
]