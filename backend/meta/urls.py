from django.urls import path
from .views import MetaWebhookView

urlpatterns = [
    # URL a ser configurada na plataforma Meta.
    path('webhook/', MetaWebhookView.as_view(), name='meta-webhook'),
]