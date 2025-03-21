import os
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor, Json

# Establish database connection
def get_db_connection():
    """Connects to the PostgreSQL database and returns the connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DATABASE"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            cursor_factory=RealDictCursor  # Enables returning query results as dictionaries
        )
        return conn
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        return None

# Get user session from the database
def get_session(user_id: str):
    """Retrieves a session for a given user from the database."""
    conn = get_db_connection()
    if conn is None:
        return None  # If connection fails, return None

    cursor = conn.cursor()
    
    # Check if session exists
    cursor.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
    session = cursor.fetchone()

    if session:
        # Convert JSON to DataFrame if 'df' column exists
        if session.get("df"):
            session["df"] = pd.DataFrame(session["df"])
    else:
        # If session does not exist, create a new one
        cursor.execute("""
            INSERT INTO sessions (user_id, df, queries, answers)
            VALUES (%s, %s, %s, %s)
        """, (user_id, Json(None), [], []))
        conn.commit()

        # Retrieve the newly created session
        cursor.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
        session = cursor.fetchone()

    cursor.close()
    conn.close()
    return session

# Update session data
def update_session(user_id: str, key: str, value):
    """Updates a session entry for a user in the database."""
    conn = get_db_connection()
    if conn is None:
        return  # If connection fails, exit function

    cursor = conn.cursor()

    if key == "df":
        if value is None:
            cursor.execute("UPDATE sessions SET df = NULL WHERE user_id = %s", (user_id,))
        elif isinstance(value, pd.DataFrame):
            df_json = value.to_dict(orient="records")  # Convert DataFrame to JSON
            cursor.execute("UPDATE sessions SET df = %s WHERE user_id = %s", (Json(df_json), user_id))
    elif key == "queries":
        cursor.execute("UPDATE sessions SET queries = %s WHERE user_id = %s", (value, user_id))
    elif key == "answers":
        cursor.execute("UPDATE sessions SET answers = %s WHERE user_id = %s", (Json(value), user_id))
    else:
        print(f"⚠️ Ignored update for unsupported key: {key}")

    conn.commit()
    cursor.close()
    conn.close()

# Clear session for a user
def clear_session(user_id: str):
    """Deletes a user's session from the database."""
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
