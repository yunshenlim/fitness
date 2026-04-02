-- ─────────────────────────────────────────────
-- Bio-OS 2026 — Database Schema
-- Run in Supabase SQL Editor (or psql)
-- ─────────────────────────────────────────────

-- Enable UUID helper (already on by default in Supabase)
create extension if not exists "pgcrypto";

-- ── fitness_logs ──────────────────────────────
create table if not exists fitness_logs (
  id          uuid        primary key default gen_random_uuid(),
  user_id     text        not null,
  exercise    text        not null,
  weight_kg   numeric(6,2),
  sets        smallint,
  reps        smallint,
  notes       text,
  created_at  timestamptz not null default now()
);

create index on fitness_logs (user_id, created_at desc);

-- ── body_stats ────────────────────────────────
create table if not exists body_stats (
  id                  uuid        primary key default gen_random_uuid(),
  user_id             text        not null,
  -- Evolt-standard fields (nullable — Gemini extracts what's available)
  body_fat_percent    numeric(5,2),
  muscle_mass_kg      numeric(6,2),
  visceral_fat_level  smallint,
  bmr_kcal            smallint,
  total_body_water_l  numeric(5,2),
  bone_mass_kg        numeric(5,2),
  -- catch-all for any extra metrics Gemini finds
  extra               jsonb,
  created_at          timestamptz not null default now()
);

create index on body_stats (user_id, created_at desc);

-- ── admin_events ──────────────────────────────
create table if not exists admin_events (
  id          uuid        primary key default gen_random_uuid(),
  user_id     text        not null,
  event_type  text        not null,   -- e.g. 'discipline_tick'
  metadata    jsonb,
  created_at  timestamptz not null default now()
);

create index on admin_events (user_id, event_type, created_at desc);

-- ── Row-Level Security (optional but recommended) ─────────────────────────────
-- alter table fitness_logs enable row level security;
-- alter table body_stats    enable row level security;
-- alter table admin_events  enable row level security;
-- 
-- create policy "owner only" on fitness_logs for all
--   using (user_id = auth.uid()::text);
-- (repeat for other tables)
