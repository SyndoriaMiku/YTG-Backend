from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from Backend import models


class AuthTests(APITestCase):
    def setUp(self):
        self.password = 'StrongPass123!'
        self.user = models.UserProfile.objects.create_user(
            username='user1', password=self.password, nickname='user1nick'
        )

    def test_register(self):
        url = reverse('register')
        resp = self.client.post(url, {
            'username': 'newuser',
            'password': 'NewPass123!',
            'email': '',
            'phone': ''
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.UserProfile.objects.filter(username='newuser').exists())

    def test_login_and_logout(self):
        login_url = reverse('login')
        resp = self.client.post(login_url, {'username': self.user.username, 'password': self.password}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        refresh = resp.data['refresh']

        logout_url = reverse('logout')
        resp2 = self.client.post(logout_url, {'refresh': refresh}, format='json')
        self.assertIn(resp2.status_code, [status.HTTP_205_RESET_CONTENT, status.HTTP_200_OK])


