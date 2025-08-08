from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('point/adjust/', views.AdminAdjustPointAPIView.as_view(), name='point_adjust'),
    path('tournament/add', views.AdminTournamentResultAPIView.as_view(), name='tournament_add'),

    #user path
    path('user/points/', views.UserPointAPIView.as_view(), name='user_points'),
    path('user/points/history/', views.PointTransactionHistoryAPIView.as_view(), name='point_transaction_history'),
    path('user/point/redeem/', views.RedeemRewardAPIView.as_view(), name='point_redeem')
]
