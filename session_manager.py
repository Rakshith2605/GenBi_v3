import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import pandas as pd

# Load Firebase credentials from environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("FIREBASE_CREDENTIALS environment variable is missing")

try:
    cred_dict = json.loads(firebase_credentials)  # Parse JSON string

    # 🔹 Check if Firebase is already initialized before calling initialize_app()
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    db = firestore.client()  # Firestore client
except Exception as e:
    raise ValueError(f"Error initializing Firebase: {e}")


def get_session(user_id: str):
    """Retrieve session from Firestore or create a new one."""
    doc_ref = db.collection("sessions").document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        session_data = doc.to_dict()
        if "df" in session_data and session_data["df"]:
            session_data["df"] = pd.DataFrame.from_dict(session_data["df"])
        return session_data
    else:
        session_data = {"df": None, "queries": [], "answers": []}
        doc_ref.set(session_data)  # Store in Firestore
        return session_data


def update_session(user_id: str, key: str, value):
    """Update a specific key in the user's session in Firestore."""
    doc_ref = db.collection("sessions").document(user_id)

    # Convert DataFrame to dictionary before storing
    if isinstance(value, pd.DataFrame):
        value = value.to_dict(orient="records")

    doc_ref.set({key: value}, merge=True)  # Use merge=True to avoid overwriting
