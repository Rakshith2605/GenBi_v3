import os
import uuid
import psycopg2
import pandas as pd
from io import BytesIO
from psycopg2.extras import RealDictCursor, Json
from supabase import create_client, Client
from dotenv import load_dotenv
import traceback
import time

# Load .env variables
load_dotenv()

# Environment variables with debug output
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "genbidf")
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"📊 Debug - SUPABASE_URL: {SUPABASE_URL}")
print(f"📊 Debug - SUPABASE_BUCKET: {SUPABASE_BUCKET}")
print(f"📊 Debug - DATABASE_URL: {DATABASE_URL and DATABASE_URL[:20]}...")  # Only print start of URL for security

# Initialize Supabase Client with retry logic
def get_supabase_client():
    """Gets a Supabase client with retry logic."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Test the client with a simple operation
            try:
                client.auth.get_session()
            except:
                # Some operations might fail but the client could still be usable
                pass
            return client
        except Exception as e:
            print(f"⚠️ Supabase client creation failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("❌ All attempts to create Supabase client failed")
                raise
    
    return None

# Try to initialize Supabase client
try:
    supabase: Client = get_supabase_client()
    # Check if bucket exists and create if needed
    try:
        buckets = supabase.storage.list_buckets()
        bucket_exists = False
        
        # Check if the bucket exists
        for bucket in buckets:
            if getattr(bucket, 'name', '') == SUPABASE_BUCKET:
                bucket_exists = True
                break
                
        if not bucket_exists:
            print(f"⚠️ Bucket '{SUPABASE_BUCKET}' not found, creating it...")
            # Use the correct format for bucket creation
            supabase.storage.create_bucket(id=SUPABASE_BUCKET)
            print(f"✅ Bucket '{SUPABASE_BUCKET}' created successfully")
        else:
            print(f"✅ Bucket '{SUPABASE_BUCKET}' already exists")
    except Exception as e:
        print(f"⚠️ Error checking/creating bucket: {e}")
except Exception as e:
    print(f"❌ Failed to initialize Supabase client: {e}")
    supabase = None

def get_db_connection():
    """Connects to the PostgreSQL database using DATABASE_URL."""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Ensure DATABASE_URL is set
            if not DATABASE_URL:
                print("❌ ERROR: DATABASE_URL environment variable is not set")
                return None
            
            # Modify connection params to force IPv4 if needed    
            conn_params = {
                'cursor_factory': RealDictCursor, 
                'connect_timeout': 10,
                # Force IPv4 connections
                'host': DATABASE_URL.split('@')[1].split(':')[0],
                'hostaddr': None  # Will be resolved via IPv4
            }
            
            # Extract connection string components
            if 'postgres://' in DATABASE_URL:
                # Parse username and password
                userpass = DATABASE_URL.split('@')[0].replace('postgres://', '')
                username = userpass.split(':')[0]
                password = userpass.split(':')[1]
                
                # Parse port and database
                hostport_db = DATABASE_URL.split('@')[1]
                port = hostport_db.split(':')[1].split('/')[0]
                database = hostport_db.split('/')[1]
                
                # Add to connection params
                conn_params['user'] = username
                conn_params['password'] = password
                conn_params['port'] = port
                conn_params['dbname'] = database
                
                # Connect with parameters instead of connection string
                conn = psycopg2.connect(**conn_params)
            else:
                # Fallback to direct connection string
                conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=10)
                
            return conn
        except Exception as e:
            print(f"❌ Database connection failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("❌ All database connection attempts failed")
                traceback.print_exc()
    
    return None

def ensure_tables_exist():
    """Makes sure all required tables exist in the database."""
    if not supabase:
        print("⚠️ Supabase client not initialized, skipping table creation")
        return False
        
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, skipping table creation")
        return False
    
    cursor = conn.cursor()
    try:
        # Check if datasets table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'datasets'
            );
        """)
        datasets_exists = cursor.fetchone()["exists"]
        
        if not datasets_exists:
            print("Creating datasets table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    name TEXT NOT NULL,
                    data JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB,
                    file_type TEXT,
                    row_count INT4,
                    column_names _TEXT,
                    storage_path TEXT,
                    storage_bucket TEXT,
                    storage_id UUID
                );
                CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);
            """)
            conn.commit()
            print("✅ datasets table created successfully")
        
        # Check if chat_sessions table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chat_sessions'
            );
        """)
        chat_sessions_exists = cursor.fetchone()["exists"]
        
        if not chat_sessions_exists:
            print("Creating chat_sessions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    dataset_id UUID,
                    title TEXT,
                    metadata JSONB,
                    session_number INT4,
                    storage_path TEXT,
                    storage_metadata JSONB,
                    storage_filename TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_dataset_id ON chat_sessions(dataset_id);
            """)
            conn.commit()
            print("✅ chat_sessions table created successfully")
        
        # Check if chat_messages table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chat_messages'
            );
        """)
        chat_messages_exists = cursor.fetchone()["exists"]
        
        if not chat_messages_exists:
            print("Creating chat_messages table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID NOT NULL,
                    content JSONB NOT NULL,
                    sender TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    type TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
            """)
            conn.commit()
            print("✅ chat_messages table created successfully")
            
        return True
    except Exception as e:
        print(f"❌ ERROR creating tables: {e}")
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def upload_df_to_supabase(user_id: str, df: pd.DataFrame, file_name: str):
    """Uploads DataFrame as CSV to Supabase Storage and returns metadata."""
    if not supabase:
        print("⚠️ Supabase client not initialized, skipping file upload")
        # Return metadata without storage info
        return {
            "storage_path": None,
            "file_name": file_name,
            "file_size_mb": 0,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "error": "Supabase client not initialized"
        }
    
    try:
        # Convert DataFrame to CSV in a BytesIO buffer
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Read the content as bytes
        file_content = csv_buffer.getvalue()
        
        file_path = f"{user_id}/{uuid.uuid4()}_{file_name}"
        print(f"🔄 Attempting to upload to bucket: {SUPABASE_BUCKET}, path: {file_path}")
        
        # Upload the file
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=file_path, 
            file=file_content,  # Pass bytes content instead of BytesIO object
            file_options={"content-type": "text/csv"}
        )

        if hasattr(response, 'error') and response.error:
            raise Exception(f"❌ Upload failed: {response.error}")

        print(f"✅ File uploaded successfully to {SUPABASE_BUCKET}/{file_path}")
        return {
            "storage_path": f"{SUPABASE_BUCKET}/{file_path}",
            "file_name": file_name,
            "file_size_mb": round(len(file_content) / (1024 * 1024), 2),
            "num_rows": len(df),
            "num_columns": len(df.columns)
        }
    except Exception as e:
        print(f"❌ ERROR uploading file: {e}")
        traceback.print_exc()
        # Return metadata without storage info
        return {
            "storage_path": None,
            "file_name": file_name,
            "file_size_mb": 0,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "error": str(e)
        }

def create_dataset(user_id: str, df: pd.DataFrame, file_name: str):
    """Creates a dataset record and uploads the DataFrame to storage."""
    # Try to create tables if needed (but continue if it fails)
    ensure_tables_exist()
    
    # Upload file to storage (might return error metadata if it fails)
    storage_info = upload_df_to_supabase(user_id, df, file_name)
    
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, returning local dataset info")
        # Return a minimal dataset structure without storing in database
        dataset_id = str(uuid.uuid4())
        return {
            "dataset_id": dataset_id,
            "name": file_name,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "is_local_only": True,  # Flag to indicate not stored in DB
            "storage_info": storage_info
        }
        
    cursor = conn.cursor()
    try:
        # Extract file type from filename
        file_type = file_name.split('.')[-1] if '.' in file_name else 'unknown'
        
        # Create dataset record
        cursor.execute("""
            INSERT INTO datasets (
                user_id, name, data, metadata, file_type, 
                row_count, column_names, storage_path, storage_bucket
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            user_id,
            file_name,
            Json(df.head(10).to_dict(orient="records")),  # Store sample data
            Json(storage_info),
            file_type,
            len(df),
            df.columns.tolist(),
            storage_info.get("storage_path"),
            SUPABASE_BUCKET
        ))
        
        dataset_id = cursor.fetchone()["id"]
        conn.commit()
        
        print(f"✅ Dataset created with ID: {dataset_id}")
        return {
            "dataset_id": dataset_id,
            "name": file_name,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "storage_info": storage_info
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR creating dataset: {e}")
        traceback.print_exc()
        # Return a minimal dataset structure without storing in database
        dataset_id = str(uuid.uuid4())
        return {
            "dataset_id": dataset_id,
            "name": file_name,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "is_local_only": True,  # Flag to indicate not stored in DB
            "storage_info": storage_info,
            "error": str(e)
        }
    finally:
        cursor.close()
        conn.close()

def create_chat_session(user_id: str, dataset_id: str = None, title: str = None):
    """Creates a new chat session."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, returning local chat session info")
        # Return a minimal chat session without storing in database
        session_id = str(uuid.uuid4())
        return {
            "session_id": session_id,
            "title": title or "New Chat",
            "session_number": 1,
            "is_local_only": True,  # Flag to indicate not stored in DB
            "dataset_id": dataset_id
        }
        
    cursor = conn.cursor()
    try:
        # Get next session number for this user
        cursor.execute("""
            SELECT COALESCE(MAX(session_number), 0) + 1 as next_session 
            FROM chat_sessions 
            WHERE user_id = %s
        """, (user_id,))
        
        next_session = cursor.fetchone()["next_session"]
        
        # Use dataset name as title if not provided
        if title is None and dataset_id is not None:
            try:
                cursor.execute("SELECT name FROM datasets WHERE id = %s", (dataset_id,))
                dataset = cursor.fetchone()
                if dataset:
                    title = f"Chat about {dataset['name']}"
                else:
                    title = f"Chat session {next_session}"
            except:
                title = f"Chat session {next_session}"
        elif title is None:
            title = f"Chat session {next_session}"
        
        # Create chat session
        cursor.execute("""
            INSERT INTO chat_sessions (
                user_id, dataset_id, title, session_number, metadata
            ) VALUES (
                %s, %s, %s, %s, %s
            ) RETURNING id
        """, (
            user_id,
            dataset_id,
            title,
            next_session,
            Json({})
        ))
        
        session_id = cursor.fetchone()["id"]
        conn.commit()
        
        print(f"✅ Chat session created with ID: {session_id}")
        return {
            "session_id": session_id,
            "title": title,
            "session_number": next_session,
            "dataset_id": dataset_id
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR creating chat session: {e}")
        traceback.print_exc()
        # Return a minimal chat session without storing in database
        session_id = str(uuid.uuid4())
        return {
            "session_id": session_id,
            "title": title or "New Chat",
            "session_number": 1,
            "is_local_only": True,  # Flag to indicate not stored in DB
            "dataset_id": dataset_id,
            "error": str(e)
        }
    finally:
        cursor.close()
        conn.close()

def add_chat_message(session_id: str, sender: str, content, message_type: str = "text"):
    """Adds a message to a chat session."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, returning local message info")
        # Return a minimal message without storing in database
        message_id = str(uuid.uuid4())
        return {
            "message_id": message_id,
            "session_id": session_id,
            "sender": sender,
            "content": content,
            "type": message_type,
            "is_local_only": True  # Flag to indicate not stored in DB
        }
        
    cursor = conn.cursor()
    try:
        # Fix for sender validation - map 'assistant' to 'system' if needed
        # This is to work around the chat_messages_sender_check constraint issue
        actual_sender = 'system' if sender == 'assistant' else sender
        
        # Convert content to JSONB if it's not already
        if isinstance(content, dict) or isinstance(content, list):
            content_json = Json(content)
        else:
            content_json = Json({"text": str(content)})
        
        # Add message
        cursor.execute("""
            INSERT INTO chat_messages (
                session_id, sender, content, type
            ) VALUES (
                %s, %s, %s, %s
            ) RETURNING id
        """, (
            session_id,
            actual_sender,  # Use mapped sender value
            content_json,
            message_type
        ))
        
        message_id = cursor.fetchone()["id"]
        
        # Update session's updated_at timestamp
        cursor.execute("""
            UPDATE chat_sessions 
            SET updated_at = NOW() 
            WHERE id = %s
        """, (session_id,))
        
        conn.commit()
        
        return {
            "message_id": message_id,
            "session_id": session_id,
            "sender": sender,  # Return original sender for consistency in the API
            "content": content,
            "type": message_type
        }
        
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR adding chat message: {e}")
        traceback.print_exc()
        # Return a minimal message without storing in database
        message_id = str(uuid.uuid4())
        return {
            "message_id": message_id,
            "session_id": session_id,
            "sender": sender,
            "content": content,
            "type": message_type,
            "is_local_only": True,  # Flag to indicate not stored in DB
            "error": str(e)
        }
    finally:
        cursor.close()
        conn.close()

def get_chat_session(session_id: str, with_messages: bool = True):
    """Get a chat session and optionally its messages."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, cannot retrieve chat session")
        return None
        
    cursor = conn.cursor()
    try:
        # Get session details
        cursor.execute("""
            SELECT * FROM chat_sessions WHERE id = %s
        """, (session_id,))
        
        session = cursor.fetchone()
        if not session:
            return None
            
        result = dict(session)
        
        # Get associated dataset if any
        if session["dataset_id"]:
            cursor.execute("""
                SELECT * FROM datasets WHERE id = %s
            """, (session["dataset_id"],))
            
            dataset = cursor.fetchone()
            if dataset:
                result["dataset"] = dict(dataset)
        
        # Get messages if requested
        if with_messages:
            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = cursor.fetchall()
            # Map 'system' sender back to 'assistant' for API consistency
            result["messages"] = []
            for msg in messages:
                msg_dict = dict(msg)
                if msg_dict["sender"] == "system":
                    msg_dict["sender"] = "assistant"
                result["messages"].append(msg_dict)
        
        return result
        
    except Exception as e:
        print(f"❌ ERROR getting chat session: {e}")
        traceback.print_exc()
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_chat_sessions(user_id: str):
    """Get all chat sessions for a user."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, cannot retrieve user chat sessions")
        return []
        
    cursor = conn.cursor()
    try:
        # Get all sessions for user
        cursor.execute("""
            SELECT cs.*, d.name as dataset_name 
            FROM chat_sessions cs
            LEFT JOIN datasets d ON cs.dataset_id = d.id
            WHERE cs.user_id = %s
            ORDER BY cs.updated_at DESC
        """, (user_id,))
        
        sessions = cursor.fetchall()
        return [dict(session) for session in sessions]
        
    except Exception as e:
        print(f"❌ ERROR getting user chat sessions: {e}")
        traceback.print_exc()
        return []
    finally:
        cursor.close()
        conn.close()

def get_user_datasets(user_id: str):
    """Get all datasets for a user."""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Database connection failed, cannot retrieve user datasets")
        return []
        
    cursor = conn.cursor()
    try:
        # Get all datasets for user
        cursor.execute("""
            SELECT * FROM datasets
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (user_id,))
        
        datasets = cursor.fetchall()
        return [dict(dataset) for dataset in datasets]
        
    except Exception as e:
        print(f"❌ ERROR getting user datasets: {e}")
        traceback.print_exc()
        return []
    finally:
        cursor.close()
        conn.close()

# Backward compatibility functions for the old API
def get_session(user_id: str):
    """Fetch most recent chat session or create one."""
    # Get user's most recent chat session
    sessions = get_user_chat_sessions(user_id)
    
    if sessions:
        # Get the most recent session with messages
        session = get_chat_session(sessions[0]["id"])
        
        # Format it in the old API format
        return {
            "session_id": session["id"],
            "queries": [msg["content"] for msg in session.get("messages", []) if msg["sender"] == "user"],
            "answers": [msg["content"] for msg in session.get("messages", []) if msg["sender"] == "assistant"],
            "df": None,  # We don't store the actual DataFrame
            "df_metadata": session.get("dataset", None)
        }
    else:
        # Create a new chat session if none exist
        new_session = create_chat_session(user_id, None, "New Chat")
        if new_session:
            return {
                "session_id": new_session["session_id"],
                "queries": [],
                "answers": [],
                "df": None,
                "df_metadata": None
            }
        else:
            # Fallback to a simple dictionary if creation fails
            return {"session_id": str(uuid.uuid4()), "queries": [], "answers": [], "df": None, "df_metadata": None}

def update_session(user_id: str, key: str, value, file_name=None):
    """Updates session with new values using the new database structure."""
    # Get existing session or create new one
    session_data = get_session(user_id)
    session_id = session_data["session_id"]
    
    try:
        if key == "df":
            if value is None:
                # Nothing to do when clearing dataframe
                pass
            elif isinstance(value, pd.DataFrame):
                # If no filename provided, use a default name
                if file_name is None:
                    file_name = f"dataset_{uuid.uuid4()}.csv"
                
                # Create a new dataset entry
                dataset = create_dataset(user_id, value, file_name)
                
                if dataset:
                    # Create a new chat session with this dataset
                    new_session = create_chat_session(
                        user_id, 
                        dataset.get("dataset_id"), 
                        f"Chat about {file_name}"
                    )

        elif key == "queries" and value:
            # Add a user message to the chat
            add_chat_message(session_id, "user", value)

        elif key == "answers" and value:
            # Add an assistant message to the chat
            add_chat_message(session_id, "assistant", value)

        else:
            print(f"⚠️ Ignored update for unsupported key: {key}")

    except Exception as e:
        print(f"❌ ERROR updating session: {e}")
        traceback.print_exc()