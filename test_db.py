import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔍 Checking Environment Variables...")
print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
print(f"POSTGRES_PASSWORD: {os.getenv('POSTGRES_PASSWORD')}")

try:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DATABASE"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        sslmode="require",
        options="-c statement_timeout=5000"
    )

    cursor = conn.cursor()
    cursor.execute("SELECT NOW();")
    print("✅ Connected to Supabase PostgreSQL! Server time:", cursor.fetchone()[0])

    cursor.close()
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)
