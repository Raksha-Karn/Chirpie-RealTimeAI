import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_response(contents):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
        )
        
        return response.text
    except Exception as e:
        print("Error generating response:", e)
        return None

print(generate_response("Hello, how are you?"))