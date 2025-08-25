from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para visualizar e editar instâncias de usuário.
    Atualmente, permite acesso a qualquer usuário (AllowAny).
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    
    def get_permissions(self):
        """
        Assigns permissions based on the action.
        """
        if self.action in ['list', 'destroy', 'update', 'partial_update']:
            self.permission_classes = [permissions.IsAdminUser]
        elif self.action == 'me':
            self.permission_classes = [permissions.IsAuthenticated]
        else: # 'create'
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Endpoint customizado que retorna os dados do próprio usuário logado.
        Se o usuário não estiver logado, retornará um erro.
        """
        # Mesmo com AllowAny, esta ação só funciona se um usuário estiver logado.
        if request.user.is_authenticated:
            serializer = self.get_serializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Se não houver usuário logado, retorna uma resposta clara.
        return Response(
            {"detail": "Credenciais de autenticação não fornecidas."},
            status=status.HTTP_401_UNAUTHORIZED
        )