import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Ensure we're in the project root
sys.path.append(str(Path(__file__).parent.parent / "src"))
from f1_pipeline.core.paths import ProjectPaths

def setup_database():
    load_dotenv()
    
    # Needs a direct PostgreSQL connection string, not just the REST API URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        print("To run raw SQL schema files, you need a direct PostgreSQL connection.")
        print("Format: postgresql://postgres.[project-id]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres")
        sys.exit(1)
        
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)
        
    sql_dir = ProjectPaths().docs / "sql"
    
    # Process layers 0 through 6 in order
    for layer in range(7):
        sql_file = sql_dir / f"layer{layer}_schema.sql"
        if not sql_file.exists():
            print(f"Warning: {sql_file.name} not found, skipping.")
            continue
            
        print(f"Executing {sql_file.name}...")
        try:
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_content = f.read()
            
            # Execute the entire file
            cursor.execute(sql_content)
            print(f"Successfully applied {sql_file.name}")
        except Exception as e:
            print(f"ERROR executing {sql_file.name}:")
            print(e)
            # Continue or stop? Usually stop on schema errors
            sys.exit(1)
            
    print("\nDatabase setup complete! All layers have been applied.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_database()
