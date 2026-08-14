create extension if not exists pgcrypto;

create table if not exists seasons (
  id uuid primary key default gen_random_uuid(),
  year integer not null unique,
  created_at timestamptz not null default now()
);

create table if not exists circuits (
  id uuid primary key default gen_random_uuid(),
  circuit_code text not null unique,
  name text not null,
  country text,
  official_length_m integer,
  track_type text,
  created_at timestamptz not null default now()
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references seasons(id) on delete cascade,
  circuit_id uuid references circuits(id) on delete set null,
  event_name text not null,
  round_number integer,
  event_date date,
  created_at timestamptz not null default now(),
  unique (season_id, event_name)
);

create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  session_type text not null,
  session_date timestamptz,
  source text not null default 'fastf1',
  created_at timestamptz not null default now(),
  unique (event_id, session_type, source)
);

create table if not exists drivers (
  id uuid primary key default gen_random_uuid(),
  driver_code text not null unique,
  full_name text,
  team_name text,
  created_at timestamptz not null default now()
);

do $$
begin
  if not exists (select 1 from pg_type where typname = 'ingestion_run_status') then
    create type ingestion_run_status as enum ('started', 'success', 'failed');
  end if;
end $$;

create table if not exists ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  season integer not null,
  event_name text not null,
  session_type text not null,
  driver_code text,
  status ingestion_run_status not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error_message text,
  config_hash text,
  code_version text
);

create table if not exists raw_data_assets (
  id uuid primary key default gen_random_uuid(),
  ingestion_run_id uuid not null references ingestion_runs(id) on delete cascade,
  source text not null,
  asset_type text not null,
  season integer not null,
  event_name text not null,
  session_type text not null,
  driver_code text,
  lap_number integer,
  storage_path text not null,
  file_format text not null,
  checksum text not null,
  row_count integer,
  created_at timestamptz not null default now()
);

create index if not exists idx_ingestion_runs_lookup
  on ingestion_runs (season, event_name, session_type, driver_code, status);

create index if not exists idx_raw_assets_lookup
  on raw_data_assets (season, event_name, session_type, driver_code, source, asset_type);

create index if not exists idx_raw_assets_ingestion_run_id
  on raw_data_assets (ingestion_run_id);

create index if not exists idx_raw_assets_checksum
  on raw_data_assets (checksum);
