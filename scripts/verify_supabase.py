import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

tables = [
    "simulation_scenarios",
    "simulation_runs",
    "simulation_assets"
]

print(f"Connecting to {url}...")
for table in tables:
    try:
        response = supabase.table(table).select("*", count="exact").execute()
        print(f"Table '{table}' has {response.count} rows.")
        if response.data:
            print(f"Sample data from '{table}': {response.data[0]}")
    except Exception as e:
        print(f"Error querying table '{table}': {e}")
