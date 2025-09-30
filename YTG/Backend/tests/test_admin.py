from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from Backend import models


class AdminEndpointsTests(APITestCase):
    def setUp(self):
        self.admin = models.UserProfile.objects.create_user(
            username='admin', password='AdminPass123', nickname='adm', is_staff=True
        )
        self.user = models.UserProfile.objects.create_user(
            username='bob', password='Pass12345', nickname='bobby'
        )

    def test_point_adjust(self):
        self.client.force_authenticate(self.admin)
        url = reverse('point_adjust')
        data = {'user': self.user.username, 'points': 25, 'description': 'adjust'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.point, 25)

    def test_tournament_add_and_bulk(self):
        self.client.force_authenticate(self.admin)

        # single add
        url_add = reverse('tournament_add')
        payload = {
            'user': self.user.username,
            'tournament_name': 'Local Cup',
            'position': '1st',
            'point_earned': 10,
            'ranking_point_earned': 15,
        }
        r1 = self.client.post(url_add, payload, format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertEqual(self.user.point, 10)
        self.assertEqual(self.user.ranking_point, 15)

        # bulk add
        url_bulk = reverse('tournament_bulk')
        items = [
            {
                'nickname': self.user.nickname,
                'tournament_name': 'City Open',
                'position': '2nd',
                'point_earned': 5,
                'ranking_point_earned': 8,
            }
        ]
        r2 = self.client.post(url_bulk, items, format='json')
        self.assertIn(r2.status_code, [status.HTTP_201_CREATED, status.HTTP_207_MULTI_STATUS])
        self.user.refresh_from_db()
        self.assertEqual(self.user.point, 15)
        self.assertEqual(self.user.ranking_point, 23)


