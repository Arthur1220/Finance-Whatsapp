import uuid
from django.db import models
from django.conf import settings

from ai.models import AILog

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    whatsapp_message_id = models.CharField(max_length=255, unique=True, db_index=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages')
    replied_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    DIRECTION_CHOICES = [
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
    ]
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='INBOUND')
    
    body = models.TextField(null=True, blank=True)
    generated_by_log = models.OneToOneField(AILog, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_message')
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message ({self.direction}) from {self.sender.username} at {self.timestamp}"

    class Meta:
        ordering = ['-created_at']