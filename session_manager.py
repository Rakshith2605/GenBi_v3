import os
import pandas as pd
import psycopg2
import json
from psycopg2.extras import RealDictCursor, Json

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DATABASE"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

def get_session(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
    session = cursor.fetchone()

    if session:
        # Convert JSON to DataFrame
        if session.get("df"):
            session["df"] = pd.DataFrame(session["df"])
        return session
    else:
        # Create a blank session
        cursor.execute("""
            INSERT INTO sessions (user_id, df, queries, answers)
            VALUES (%s, %s, %s, %s)
        """, (user_id, Json(None), [], []))
        conn.commit()
        cursor.close()
        conn.close()
        return {"df": None, "queries": [], "answers": []}

def update_session(user_id: str, key: str, value):
    conn = get_db_connection()
    cursor = conn.cursor()

    if key == "df":
        if value is None:
            cursor.execute("UPDATE sessions SET df = NULL WHERE user_id = %s", (user_id,))
        elif isinstance(value, pd.DataFrame):
            df_json = value.to_dict(orient="records")
            cursor.execute("UPDATE sessions SET df = %s WHERE user_id = %s", (Json(df_json), user_id))
    elif key == "queries":
        cursor.execute("UPDATE sessions SET queries = %s WHERE user_id = %s", (value, user_id))
    elif key == "answers":
        cursor.execute("UPDATE sessions SET answers = %s WHERE user_id = %s", (Json(value), user_id))
    else:
        print(f"Ignored update for unsupported key: {key}")

    conn.commit()
    cursor.close()
    conn.close()
