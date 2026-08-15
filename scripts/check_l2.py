import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

res = supabase.table("feature_runs").select("*").order("started_at", desc=True).limit(1).execute()
print("Latest Feature Run:", res.data)

res = supabase.table("feature_assets").select("*").order("created_at", desc=True).limit(5).execute()
print("Feature Assets:", res.data)
