from asgiref.sync import async_to_sync
from .models import ChatMessage
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
import json
import os
import threading
import time
from threading import Lock
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

ai_lock = Lock()
ai_is_responding = False

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "gay"
        self.accept()
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        
        self.send(text_data=json.dumps({
            "type": "connection_status",
            "status": "connected",
            "ai_responding": ai_is_responding
        }))
    
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )
    
    def receive(self, text_data):
        global ai_is_responding
        
        text_data_json = json.loads(text_data)
        message = text_data_json.get("message", "")
        user_id = text_data_json.get("user_id")
        
        if ai_is_responding:
            self.send(text_data=json.dumps({
                "type": "ai_status",
                "status": "busy",
                "message": "AI is currently responding to another message. Please wait."
            }))
            return
            
        username = "Anonymous"
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                username = user.username
                self.save_message(user_id, message)
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
        
        if message.lower().startswith("@ai") or message.lower().startswith("ai:"):
            with ai_lock:
                ai_is_responding = True
            
            try:
                ai_user = User.objects.get(username="AI_Assistant")
            except User.DoesNotExist:
                ai_user = User.objects.create_user(
                    username="AI_Assistant",
                    password=os.urandom(24).hex(),
                    email="ai@example.com"
                )
            
            placeholder_message = "..."
            ai_message = ChatMessage.objects.create(user=ai_user, message=placeholder_message)
            
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "chat_message",
                    "username": "AI_Assistant",
                    "message": placeholder_message,
                    "message_id": ai_message.id,
                    "is_placeholder": True
                }
            )
            
            self.start_thinking_animation(ai_message.id)
            
            chat_history = self.get_chat_history(10)  
            
            threading.Thread(
                target=self.generate_ai_response,
                args=(message, username, chat_history, ai_message.id)
            ).start()
    
    def start_thinking_animation(self, message_id):
        def send_thinking():
            thinking_states = [".", "..", "...", "thinking...", "thinking....", "thinking....."]
            for i in range(20):
                if not ai_is_responding:
                    break
                
                state = thinking_states[i % len(thinking_states)]
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "update_ai_message",
                        "message_id": message_id,
                        "content": state,
                        "is_thinking": True
                    }
                )
                time.sleep(0.02)
        
        threading.Thread(target=send_thinking).start()
    
    def generate_ai_response(self, user_message, username, chat_history, message_id):
        global ai_is_responding
        
        try:
            context = "\n".join([f"{msg.user.username}: {msg.message}" for msg in chat_history])
            
            prompt = f"""
            You are a great problem solver, helper and a great friend. You are talking to multiple users who can see each other's messages.
            The most recent message is from {username}: {user_message}
            
            Recent chat history:
            {context}
            
            Please provide a detailed, helpful and friendly response to {username}'s message, considering the context of the conversation. Act like you're a cool friend. Do not repeat the @AI tag.
            """
            
            streaming_response = self.generate_streaming_response(prompt, message_id)
            
            try:
                ai_message = ChatMessage.objects.get(id=message_id)
                ai_message.message = streaming_response
                ai_message.save()
            except ChatMessage.DoesNotExist:
                print(f"Message with id {message_id} does not exist")
            
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "update_ai_message",
                    "message_id": message_id,
                    "content": streaming_response,
                    "is_final": True
                }
            )
        
        except Exception as e:
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "update_ai_message",
                    "message_id": message_id,
                    "content": f"Error generating response: {str(e)}",
                    "is_error": True
                }
            )
        
        finally:
            with ai_lock:
                ai_is_responding = False
            
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "ai_status_update",
                    "status": "idle",
                    "message": "AI is ready for new questions"
                }
            )
    
    def generate_streaming_response(self, prompt, message_id):
        try:
            response = client.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            collected_response = ""
            for chunk in response:
                if hasattr(chunk, 'text'):
                    chunk_text = chunk.text
                    collected_response += chunk_text
                    
                    async_to_sync(self.channel_layer.group_send)(
                        self.group_name,
                        {
                            "type": "update_ai_message",
                            "message_id": message_id,
                            "content": collected_response
                        }
                    )
                    
                    time.sleep(0.1)
            
            return collected_response
        
        except Exception as e:
            print("Error generating response:", e)
            return f"Sorry, I encountered an error: {str(e)}"
    
    def get_chat_history(self, limit=10):
        return ChatMessage.objects.all().order_by("created_at")[:limit]
    
    def chat_message(self, event):
        message = event.get("message", "")
        username = event.get("username", "Anonymous")
        message_id = event.get("message_id", None)
        is_placeholder = event.get("is_placeholder", False)
        
        self.send(text_data=json.dumps({
            "type": "chat_message",
            "username": username,
            "message": message,
            "message_id": message_id,
            "is_placeholder": is_placeholder
        }))
    
    def update_ai_message(self, event):
        message_id = event.get("message_id")
        content = event.get("content", "")
        is_thinking = event.get("is_thinking", False)
        is_final = event.get("is_final", False)
        is_error = event.get("is_error", False)
        
        self.send(text_data=json.dumps({
            "type": "update_ai_message",
            "message_id": message_id,
            "content": content,
            "is_thinking": is_thinking,
            "is_final": is_final,
            "is_error": is_error
        }))
    
    def ai_status_update(self, event):
        self.send(text_data=json.dumps({
            "type": "ai_status",
            "status": event.get("status"),
            "message": event.get("message")
        }))
    
    def save_message(self, user_id, message):
        try:
            user = User.objects.get(id=user_id)
            ChatMessage.objects.create(user=user, message=message)
        except User.DoesNotExist:
            print(f"User with id {user_id} does not exist")