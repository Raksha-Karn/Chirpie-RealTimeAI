from asgiref.sync import async_to_sync
from .models import ChatMessage
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
import json


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "gay"
        self.accept()
        
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )
        
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get("message", "")
        user_id = text_data_json.get("user_id")
        
        if user_id:
            self.save_message(user_id, message)
        
        username = "Anonymous"
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                username = user.username
            except User.DoesNotExist:
                print(f"User with id {user_id} does not exist")
        
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_message",
                "username": username,
                "message": message,
            }
        )
        
    def chat_message(self, event):
        message = event.get("message", "")
        username = event.get("username", "Anonymous")
        
        self.send(text_data=json.dumps({
            "type": "chat_message",
            "username": username,
            "message": message,
        }))
        
    def save_message(self, user_id, message):
        try:
            user = User.objects.get(id=user_id)
            ChatMessage.objects.create(user=user, message=message)
        except User.DoesNotExist:
            print(f"User with id {user_id} does not exist")