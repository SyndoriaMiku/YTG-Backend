from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from Backend import models


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = models.UserProfile.objects.create_user(
            username='u1', password='Pass12345', nickname='nick1', email='u1@example.com'
        )

    def test_get_points_and_history(self):
        self.client.force_authenticate(self.user)

        # Seed a transaction
        models.PointTransaction.objects.create(user=self.user, points=10, description='seed')

        url_info = reverse('user_info')  # Fixed URL name
        resp = self.client.get(url_info)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], self.user.username)

        url_hist = reverse('point_transaction_history')
        resp2 = self.client.get(url_hist)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(resp2.data, list))

    def test_update_profile(self):
        self.client.force_authenticate(self.user)
        # Test that user can change nickname initially
        self.assertTrue(self.user.check_name_change_limit())
        
        url = reverse('user_update')  # Fixed URL name
        # Test nickname update
        resp = self.client.patch(url, {'nickname': 'new_nick'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, 'new_nick')
        
        # After changing nickname, check that limit is now in effect
        self.assertFalse(self.user.check_name_change_limit())


