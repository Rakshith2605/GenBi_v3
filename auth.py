import os
import jwt
from fastapi import Header, HTTPException
from dotenv import load_dotenv

# Load .env file
load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise Exception("❌ ERROR: `SUPABASE_JWT_SECRET` is missing!")

print("✅ Loaded SUPABASE_JWT_SECRET:", SUPABASE_JWT_SECRET[:10] + "******")

def verify_supabase_token(authorization: str = Header(...)):
    print("🔍 Received Token:", authorization)

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")

    token = authorization.split("Bearer ")[1]

    try:
        decoded_token = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Try disabling audience verification
        )
        print("✅ Token Decoded Successfully:", decoded_token)
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token verification error: {str(e)}")
