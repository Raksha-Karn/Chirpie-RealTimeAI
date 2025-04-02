import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")

try:
    conn = psycopg2.connect(
        dbname=DATABASE_NAME,
        user=DATABASE_USERNAME,
        password=DATABASE_PASSWORD,
        host=DATABASE_HOST,
        port=DATABASE_PORT
    )
    
    cursor = conn.cursor()
    cursor = conn.cursor()
    
    cursor.execute("SELECT version();")
    
    record = cursor.fetchone()
    print("Connected to:", record)
    
    cursor.close()
    conn.close()

except Exception as e:
    print("Error connecting to the database:", e)