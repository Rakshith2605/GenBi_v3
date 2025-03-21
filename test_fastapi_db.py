import os
import psycopg2

try:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DATABASE"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        sslmode="require",
    )
    print("✅ FastAPI Successfully Connected to Supabase!")
    conn.close()
except Exception as e:
    print("❌ FastAPI Connection Failed:", e)
