from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('point/add/', views.PointAddAPIView.as_view(), name='point_add'),
    path('tournament/add', views.TournamentAddAPIView.as_view(), name='tournament_add'),
]
