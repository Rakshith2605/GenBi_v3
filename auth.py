import os
import jwt
from fastapi import Header, HTTPException
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()
SUPABASE_JWT_SECRET = "ueiMuGwYxllQiLfbl+QDDj2Ed0XESle6F5r1z6UBR7f73nIYQTI3PPX0WNl2wZOYOkBrxArngEwaNmaSI+jFUg=="

# ✅ Print environment variable directly
print("\n🔍 DEBUG: `SUPABASE_JWT_SECRET` from os.getenv:", SUPABASE_JWT_SECRET)

# ✅ Ensure the correct secret is loaded
if not SUPABASE_JWT_SECRET:
    raise Exception("❌ ERROR: `SUPABASE_JWT_SECRET` is missing!")

print("✅ DEBUG: Loaded SUPABASE_JWT_SECRET:", SUPABASE_JWT_SECRET[:10] + "******")  # Print part of the secret

def verify_supabase_token(authorization: str = Header(...)):
    print("\n🔍 DEBUG: Received Authorization Header:", authorization)

    if not authorization.startswith("Bearer "):
        print("❌ ERROR: Authorization header format is incorrect.")
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")

    token = authorization.split("Bearer ")[1]
    print("🔑 DEBUG: Extracted Token:", token[:30] + "...")  # Print part of the token

    try:
        decoded_token = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",  # ✅ Ensure this matches the token's "aud"
        )
        print("✅ DEBUG: Token Decoded Successfully:", decoded_token)
        return decoded_token
    except jwt.ExpiredSignatureError:
        print("❌ ERROR: Token Expired!")
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError as e:
        print(f"❌ ERROR: Invalid Token! {e}")
        raise HTTPException(status_code=401, detail="Invalid token.")
