import os
import uuid
import psycopg2
import pandas as pd
from io import BytesIO
from psycopg2.extras import RealDictCursor, Json
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# ✅ Correct Supabase API Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use the correct service key
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "genbi-df")

# ✅ Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Fix PostgreSQL Connection using DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")  # Ensure DATABASE_URL is in your .env

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Connects to the PostgreSQL database using DATABASE_URL."""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:YOUR-PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        return None


def upload_df_to_supabase(user_id: str, df: pd.DataFrame, file_name: str):
    """Uploads DataFrame as CSV to Supabase Storage and returns metadata."""
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    file_path = f"{user_id}/{uuid.uuid4()}_{file_name}"

    # ✅ Fix: Upload and check for errors correctly
    response = supabase.storage.from_(SUPABASE_BUCKET).upload(file_path, csv_buffer, {"content-type": "text/csv"})

    if response.error:
        raise Exception(f"❌ Upload failed: {response.error}")

    return {
        "storage_path": f"{SUPABASE_BUCKET}/{file_path}",
        "file_name": file_name,
        "file_size_mb": round(csv_buffer.getbuffer().nbytes / (1024 * 1024), 2),
        "num_rows": df.shape[0],
        "num_columns": df.shape[1]
    }


def get_session(user_id: str):
    """Fetch or create a session for a user."""
    conn = get_db_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
    session = cursor.fetchone()

    if session:
        session_data = {
            "session_id": session["session_id"],
            "df_metadata": session["df_metadata"],
            "queries": session["queries"] if session["queries"] else [],
            "answers": session["answers"] if session["answers"] else [],
        }
    else:
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, df_metadata, queries, answers) VALUES (gen_random_uuid(), %s, %s, %s, %s) RETURNING session_id",
            (user_id, Json(None), Json([]), Json([]))
        )
        session_id = cursor.fetchone()["session_id"]
        conn.commit()
        session_data = {"session_id": session_id, "df_metadata": None, "queries": [], "answers": []}

    cursor.close()
    conn.close()
    return session_data


def update_session(session_id: str, key: str, value, user_id=None, file_name=None):
    """Updates session with new values."""
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()

    if key == "df":
        if value is None:
            cursor.execute("UPDATE sessions SET df_metadata = NULL WHERE session_id = %s", (session_id,))
        elif isinstance(value, pd.DataFrame):
            metadata = upload_df_to_supabase(user_id, value, file_name)
            cursor.execute("UPDATE sessions SET df_metadata = %s WHERE session_id = %s", (Json(metadata), session_id))

    elif key == "queries":
        cursor.execute(
            "UPDATE sessions SET queries = COALESCE(queries, '[]'::jsonb) || %s WHERE session_id = %s",
            (Json(value), session_id)
        )

    elif key == "answers":
        cursor.execute(
            "UPDATE sessions SET answers = COALESCE(answers, '[]'::jsonb) || %s WHERE session_id = %s",
            (Json(value), session_id)
        )

    else:
        print(f"⚠️ Ignored update for unsupported key: {key}")

    conn.commit()
    cursor.close()
    conn.close()
