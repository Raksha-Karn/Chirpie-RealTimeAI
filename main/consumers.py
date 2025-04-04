from asgiref.sync import async_to_sync
from .models import ChatMessage
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User
import json
import os
from dotenv import load_dotenv
from google import genai
from threading import Lock

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
                "message": "AI is currently processing a request. Please wait for it to finish."
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
                
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "ai_status_update",
                    "status": "responding",
                    "message": "AI is thinking.."
                }
            )
            
            chat_history = self.get_chat_history(10)
            self.generate_ai_response(message, username, chat_history)
            
    def generate_ai_response(self, user_message, username, chat_history):
        global ai_is_responding
        
        try:
            context = "\n".join([f"{msg.user.username}: {msg.message}" for msg in chat_history])
            prompt = f"""
                You are an AI assistant in a group chat. You are talking to multiple users who can see each other's messages.
                The most recent message is from {username}: {user_message}
                
                Recent chat history:
                {context}
                
                Please provide a helpful response to {username}'s message, considering the context of the conversation.
            """
            
            response = self.generate_response(prompt)
            
            if response:
                try:
                    ai_user = User.objects.get(username="AI_Assistant")
                except User.DoesNotExist:
                    ai_user = User.objects.create_user(username="AI_Assistant", password=os.urandom(24).hex(), email="ai@gmail.com")
            
                self.save_message(ai_user.id, response)
                
                async_to_sync(self.channel_layer.group_send)(
                    self.group_name,
                    {
                        "type": "chat_message",
                        "username": "AI_Assistant",
                        "message": response
                    }
                )
            
        except Exception as e:
            async_to_sync(self.channel_layer.group_send)(
                self.group_name,
                {
                    "type": "chat_message",
                    "username": "System",
                    "message": "Error generating response: " + str(e)
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
                    "message": "AI is ready for new questions."
                }
            )
    
    def generate_response(self, prompt):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            if hasattr(response, 'text'):
                return response.text
            
            if hasattr(response, 'parts'):
                collected_response = ""
                for part in response.parts:
                    if hasattr(part, 'text'):
                        collected_response += part.text
                return collected_response
            
            return "I couldn't generate a response at the moment."
        
        except Exception as e:
            print("Error generating response:", e)
            return f"Sorry, I encountered an error: {str(e)}"
        
    def get_chat_history(self, limit=10):
        try:
            return ChatMessage.objects.all().order_by("created_at")[:limit]
        except Exception as e:
            print("Error retrieving chat history:", e)
            return []
        
    def ai_status_update(self, event):
        self.send(text_data=json.dumps({
            "type": "ai_status",
            "status": event.get("status", "idle"),
            "message": event.get("message", "AI is ready for new questions.")
        }))
        
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