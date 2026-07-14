from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.profile_url = '/api/auth/profile/'
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'securepassword123',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_user_registration(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')

    def test_user_login(self):
        # Register first
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Login
        login_data = {
            'username': 'testuser',
            'password': 'securepassword123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_access_profile_protected(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Login to get token
        self.client.post(self.register_url, self.user_data, format='json')
        login_data = {'username': 'testuser', 'password': 'securepassword123'}
        login_response = self.client.post(self.login_url, login_data, format='json')
        token = login_response.data['access']
        
        # Make authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
