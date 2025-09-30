from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from Backend import models


class RewardsTests(APITestCase):
    def setUp(self):
        self.admin = models.UserProfile.objects.create_user(
            username='admin', password='AdminPass123', nickname='adm', is_staff=True
        )
        self.user = models.UserProfile.objects.create_user(
            username='alice', password='Pass12345', nickname='alicek'
        )
        self.reward = models.Reward.objects.create(name='Sleeves', cost=10, stock=2)

    def test_redeem_and_admin_confirm_cancel(self):
        # user redeem
        self.client.force_authenticate(self.user)
        url_redeem = reverse('point_redeem')
        r1 = self.client.post(url_redeem, {'reward': self.reward.id}, format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        redemption_id = r1.data['redemption_id']

        # give user enough points then admin confirm
        self.user.point = 20
        self.user.save()

        self.client.force_authenticate(self.admin)
        from Backend.views import AdminRedemptionAPIView, AdminCancelRedemptionAPIView  # ensure routes exist

        url_confirm = reverse('monthly_ranking').replace('ranking/monthly/', f'redemption/{redemption_id}/confirm')
        # If not routed, call via pattern used in project; here just ensure status change works through view
        view = AdminRedemptionAPIView.as_view()
        request = self.client.post(url_confirm)



