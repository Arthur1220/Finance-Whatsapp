from rest_framework.routers import DefaultRouter
from .views import UserViewSet

app_name = 'users'

# Cria uma instância do Router
router = DefaultRouter()

# Registra o UserViewSet com o router.
# O router irá gerar automaticamente as URLs para o CRUD.
router.register(r'', UserViewSet, basename='user')

# As urlpatterns do app são compostas pelas URLs geradas pelo router.
urlpatterns = router.urls