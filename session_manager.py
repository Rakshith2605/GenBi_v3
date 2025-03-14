import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Load Firebase credentials from environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_credentials:
    raise ValueError("FIREBASE_CREDENTIALS environment variable is missing")

try:
    cred_dict = json.loads(firebase_credentials)  # Parse JSON string
    # Initialize Firebase only once
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    db = firestore.client()  # Firestore client
except Exception as e:
    raise ValueError(f"Error initializing Firebase: {e}")

def get_session(user_id: str):
    """Retrieve session from Firestore or create a new one, storing only queries and answers."""
    doc_ref = db.collection("sessions").document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        session_data = doc.to_dict()
        # Ensure that any legacy data for uploaded files (e.g. "df") is removed
        session_data.pop("df", None)
        return session_data
    else:
        session_data = {"queries": [], "answers": []}
        doc_ref.set(session_data)
        return session_data

def update_session(user_id: str, key: str, value):
    """Update a specific key in the user's session in Firestore.
       Only 'queries' and 'answers' fields are allowed.
    """
    allowed_keys = {"queries", "answers"}
    if key not in allowed_keys:
        # Ignore updates for keys that are not allowed
        return

    doc_ref = db.collection("sessions").document(user_id)
    doc_ref.set({key: value}, merge=True)
