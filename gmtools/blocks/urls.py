#from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.listblocks, name="listblocks"),
    path('<int:group_id>', views.showblock,name='showblock')
]
