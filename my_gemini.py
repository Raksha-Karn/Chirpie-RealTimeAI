import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def generate_response(contents):
    try:
        response = client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=contents,
        )
        collected_response = ""
        for chunk in response:
            if hasattr(chunk, 'text'):
                chunk_text = chunk.text
                print(chunk_text, end="", flush=True)
                collected_response += chunk_text
            
        print("\n")
        return collected_response
    except Exception as e:
        print("Error generating response:", e)
        return None
generate_response("Write a poem about a cat")