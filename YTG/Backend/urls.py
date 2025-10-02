from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    #admin path
    path('users/', views.UserListAPIView.as_view(), name='user_list'),
    path('point/adjust/', views.AdminAdjustPointAPIView.as_view(), name='point_adjust'),
    path('tournament/add/', views.AdminTournamentResultAPIView.as_view(), name='tournament_add'),
    path('tournament/bulk/', views.AdminTournamentBulkUpdateAPIView.as_view(), name='tournament_bulk'),
    path('admin/users/<str:username>/', views.AdminUserUpdateAPIView.as_view(), name='admin_user_update'),
    path('admin/redemption/<int:redemption_id>/confirm/', views.AdminRedemptionAPIView.as_view(), name='admin_confirm_redemption'),
    path('admin/redemption/<int:redemption_id>/cancel/', views.AdminCancelRedemptionAPIView.as_view(), name='admin_cancel_redemption'),

    #user path
    path('user/', views.UserAPIView.as_view(), name='user_info'),
    path('user/password/change/', views.UpdatePasswordAPIView.as_view(), name='change_password'),
    path('user/points/history/', views.PointTransactionHistoryAPIView.as_view(), name='point_transaction_history'),
    path('user/point/redeem/', views.RedeemRewardAPIView.as_view(), name='point_redeem'),
    path('user/update/', views.UserProfileUpdateAPIView.as_view(), name='user_update'),
    path('user/orders/', views.UserOrderView.as_view(), name='user_orders'),
    path('user/orders/<int:order_id>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('user/orders/<int:order_id>/cancel/', views.CancelOrderAPIView.as_view(), name='cancel_order'),
    path('orders/create/', views.CreateOrderAPIView.as_view(), name='create_order'),

    #guest path
    path('ranking/monthly/', views.MonthlyRankingAPIView.as_view(), name='monthly_ranking'),
    path('ranking/user/', views.UserRankingAPIView.as_view(), name='user_ranking'),
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout')
]
