from django.urls import path

from . import views

urlpatterns = [
    path('item_list/', views.itemListView.as_view()),
    path('item_detail/<int:pk>/', views.itemDetailView.as_view()),
]