from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
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
        
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_message",
                "message": message,
            }
        )
        
    def chat_message(self, event):
        message = event.get("message", "")
        self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": message,
        }))