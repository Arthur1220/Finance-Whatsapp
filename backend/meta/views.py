from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

# Import the new task
from .tasks import process_webhook_payload

class MetaWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # GET method remains the same
        verify_token = settings.META_VERIFY_TOKEN
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')
        if mode == 'subscribe' and token == verify_token:
            print("WEBHOOK_VERIFIED")
            return HttpResponse(challenge, status=200)
        print("WEBHOOK_VERIFICATION_FAILED")
        return HttpResponse('Error, wrong validation token', status=403)

    def post(self, request):
        """
        Receives the webhook payload and sends it to a Celery task for background processing.
        Responds immediately with a 200 OK.
        """
        payload = request.data
        
        # This is the magic: .delay() sends the job to the Celery queue
        process_webhook_payload.delay(payload)
        
        print("Webhook received and tasked to Celery worker. Responding 200 OK.")
        return Response(status=status.HTTP_200_OK)