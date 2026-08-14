from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseConfigurationError(RuntimeError):
    pass


class SupabaseConnectionError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", service_role_key),
        )
        if not value
    ]
    if missing:
        raise SupabaseConfigurationError(
            f"Missing required Supabase environment variables: {', '.join(missing)}"
        )

    parsed = urlparse(supabase_url or "")
    if parsed.scheme != "https" or not parsed.netloc:
        raise SupabaseConfigurationError("SUPABASE_URL must be a valid https Supabase project URL.")

    return create_client(supabase_url, service_role_key)


def health_check(client: Client | None = None) -> bool:
    db = client or get_supabase_client()
    try:
        db.table("ingestion_runs").select("id").limit(1).execute()
    except Exception as exc:
        raise SupabaseConnectionError("Could not connect to Supabase Layer 0 tables.") from exc
    return True
