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

    # Initialize Firebase only once
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    db = firestore.client()  # Firestore client
except Exception as e:
    raise ValueError(f"Error initializing Firebase: {e}")


def get_session(user_id: str):
    """Retrieve session from Firestore or create a new one.
       The session may contain a stored DataFrame ('df') along with queries and answers.
    """
    doc_ref = db.collection("sessions").document(user_id)
    doc = doc_ref.get()

    if doc.exists:
        session_data = doc.to_dict()
        # Convert stored DataFrame (if present) from dict to DataFrame
        if "df" in session_data and session_data["df"]:
            session_data["df"] = pd.DataFrame.from_dict(session_data["df"])
        return session_data
    else:
        session_data = {"df": None, "queries": [], "answers": []}
        doc_ref.set(session_data)  # Store in Firestore
        return session_data


def update_session(user_id: str, key: str, value):
    """Update a specific key in the user's session in Firestore.
    
       For the 'df' key:
         - If a new DataFrame is provided, it replaces the existing one.
         - If value is None, the stored DataFrame is removed.
       All other keys are updated normally.
    """
    doc_ref = db.collection("sessions").document(user_id)
    
    if key == "df":
        if value is None:
            # Delete the 'df' field if new value is None.
            doc_ref.update({"df": firestore.DELETE_FIELD})
        elif isinstance(value, pd.DataFrame):
            # Convert DataFrame to dictionary (list of records) and update.
            new_df = value.to_dict(orient="records")
            doc_ref.set({"df": new_df}, merge=True)
        else:
            # If the value for 'df' is not a DataFrame, ignore the update.
            return
    else:
        # For other keys (e.g., queries or answers), update normally.
        doc_ref.set({key: value}, merge=True)