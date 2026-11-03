from django.urls import path
from .views import *


urlpatterns = [
    path("auth/", AuthView.as_view()),
    path("nonauth/<str:type>/", NonAuthView.as_view()),
]
