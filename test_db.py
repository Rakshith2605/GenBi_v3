import jwt
import os

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
token = "eyJhbGciOiJIUzI1NiIsImtpZCI6Ii96TkZDTHRBWHFLTSt3QTIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z6eW10eGtocm90aG5mdXdvYmJzLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZDZkNDYwOC03ZmVhLTRjZTEtODZlYy0wYmNmNTUyMTczODMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzQyNTk0NTE3LCJpYXQiOjE3NDI1OTA5MTcsImVtYWlsIjoiZGhhcm1hcHBhLnJAbm9ydGhlYXN0ZXJuLmVkdSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJkaGFybWFwcGEuckBub3J0aGVhc3Rlcm4uZWR1IiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZpcnN0X25hbWUiOiJSYWtzaGl0aCIsImxhc3RfbmFtZSI6IkRoYXJtYXBwYSIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiMmQ2ZDQ2MDgtN2ZlYS00Y2UxLTg2ZWMtMGJjZjU1MjE3MzgzIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NDI1OTA5MTd9XSwic2Vzc2lvbl9pZCI6IjdmOTk0NDk0LWU4ZTMtNGY0Yy05ZmU4LTliZDEwMTM3MDg5OSIsImlzX2Fub255bW91cyI6ZmFsc2V9.R345iL6ogc9jjcl_eRdFLNDlvOaNy27qAA4DXp-nz6w"

try:
    decoded = jwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated"  # Make sure this matches "aud"
    )
    print("✅ Token is valid! Decoded data:", decoded)
except jwt.ExpiredSignatureError:
    print("❌ ERROR: Token Expired!")
except jwt.InvalidTokenError as e:
    print(f"❌ ERROR: Invalid Token! {e}")
