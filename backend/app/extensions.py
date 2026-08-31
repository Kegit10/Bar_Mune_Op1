import os
from supabase import create_client, Client
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

supabase: Client = create_client(url, key)

jwt = JWTManager()
