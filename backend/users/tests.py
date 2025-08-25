from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User

class UserAPITests(APITestCase):
    """
    Suite de testes para a API de Usuários.
    """

    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'StrongPassword123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_create_user(self):
        """
        Testa se um novo usuário pode ser criado via API.
        """
        # CORREÇÃO: Usamos o namespace 'users' antes do nome da URL
        url = reverse('users:user-list') 
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'AnotherPassword456'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(response.data['username'], 'newuser')

    def test_login_and_get_token(self):
        """
        Testa se um usuário existente consegue fazer login e obter um token JWT.
        """
        # A URL 'login' não tem namespace, pois está no core/urls.py
        url = reverse('login')
        
        response = self.client.post(url, {
            'username': self.user_data['username'],
            'password': self.user_data['password'],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_me_endpoint_authenticated(self):
        """
        Testa se o endpoint /me/ funciona para um usuário autenticado.
        """
        login_url = reverse('login')
        login_response = self.client.post(login_url, self.user_data, format='json')
        access_token = login_response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # CORREÇÃO: Usamos o namespace 'users' antes do nome da URL
        me_url = reverse('users:user-me') 
        response = self.client.get(me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_get_me_endpoint_unauthenticated(self):
        """
        Testa se o endpoint /me/ retorna erro para um usuário não autenticado.
        """
        # CORREÇÃO: Usamos o namespace 'users' antes do nome da URL
        url = reverse('users:user-me')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)