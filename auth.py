from fastapi import Header, HTTPException
import firebase_admin
from firebase_admin import auth, credentials
import os
import json

# Import our token model if needed
# from models.token_models import LocalTokenPayload

if not firebase_admin._apps:
    # Try to read embedded credentials from the environment variable
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
    if firebase_credentials:
        try:
            cred = credentials.Certificate(json.loads(firebase_credentials))
            firebase_admin.initialize_app(cred)
        except Exception as e:
            raise Exception(f"Failed to initialize Firebase Admin SDK with env var: {str(e)}")
    else:
        # Fallback: Read from a file (if FIREBASE_CREDENTIALS is not set)
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json")
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            raise Exception(f"Failed to initialize Firebase Admin SDK from file: {str(e)}")

def verify_firebase_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
