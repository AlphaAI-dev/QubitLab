-- Quantum Learning Platform — schema.sql
-- RLS is written in from the first migration, not retrofitted.
-- Run in dev/staging/prod separately — never share one Supabase project across envs.

create extension if not exists "uuid-ossp";

-- ============================================================
-- INSTITUTIONS
-- ============================================================
create table institutions (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  subscription_tier text not null default 'trial' check (subscription_tier in ('trial','standard','enterprise')),
  seat_count int not null default 0,
  created_at timestamptz not null default now()
);

-- ============================================================
-- USERS  (extends Supabase Auth's auth.users via 1:1 profile row)
-- ============================================================
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'student' check (role in ('student','institution_admin')),
  institution_id uuid references institutions(id) on delete set null,
  display_name text,
  created_at timestamptz not null default now()
);

-- ============================================================
-- SUBSCRIPTIONS  (individual OR institutional — plan_scope decides which FK applies)
-- ============================================================
create table subscriptions (
  id uuid primary key default uuid_generate_v4(),
  plan_scope text not null check (plan_scope in ('individual','institutional')),
  user_id uuid references profiles(id) on delete cascade,
  institution_id uuid references institutions(id) on delete cascade,
  plan text not null,
  status text not null default 'active' check (status in ('active','past_due','canceled')),
  renews_at timestamptz,
  created_at timestamptz not null default now(),
  constraint one_owner check (
    (plan_scope = 'individual' and user_id is not null and institution_id is null) or
    (plan_scope = 'institutional' and institution_id is not null and user_id is null)
  )
);

-- ============================================================
-- TOPICS  (skill tree — self-referencing prerequisite, NOT a hardcoded count)
-- ============================================================
create table topics (
  id uuid primary key default uuid_generate_v4(),
  slug text not null unique,
  title text not null,
  order_index int not null,
  prerequisite_id uuid references topics(id),
  explanation_md text not null,
  created_at timestamptz not null default now()
);

-- ============================================================
-- CHALLENGES  (per topic — grading config lives here, not in frontend)
-- ============================================================
create table challenges (
  id uuid primary key default uuid_generate_v4(),
  topic_id uuid not null references topics(id) on delete cascade,
  circuit_config jsonb not null,       -- qubit count, allowed gates, starter state
  correct_logic_ref text not null,     -- key into backend-fastapi grading registry
  tolerance_low numeric not null,      -- e.g. 0.45
  tolerance_high numeric not null,     -- e.g. 0.55
  outcome_count int not null default 2 -- drives generic N-outcome visualizer
);

-- ============================================================
-- USER PROGRESS  (server-side gating source of truth)
-- ============================================================
create table user_progress (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references profiles(id) on delete cascade,
  topic_id uuid not null references topics(id) on delete cascade,
  status text not null default 'locked' check (status in ('locked','in_progress','completed')),
  submitted_prediction jsonb,
  graded_result jsonb,
  completed_at timestamptz,
  unique (user_id, topic_id)
);

-- ============================================================
-- CHAT  (scoped per user, optionally per topic for RAG context)
-- ============================================================
create table chat_sessions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references profiles(id) on delete cascade,
  topic_id uuid references topics(id),
  created_at timestamptz not null default now()
);

create table chat_messages (
  id uuid primary key default uuid_generate_v4(),
  session_id uuid not null references chat_sessions(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table profiles enable row level security;
alter table subscriptions enable row level security;
alter table user_progress enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table institutions enable row level security;

-- profiles: a user reads/updates only their own row
create policy profiles_self on profiles
  for select using (auth.uid() = id);
create policy profiles_self_update on profiles
  for update using (auth.uid() = id);

-- institution_admins can read profiles within their own institution
create policy profiles_admin_read on profiles
  for select using (
    exists (
      select 1 from profiles admin
      where admin.id = auth.uid()
        and admin.role = 'institution_admin'
        and admin.institution_id = profiles.institution_id
    )
  );

-- institutions: readable by members of that institution only
create policy institutions_member_read on institutions
  for select using (
    exists (select 1 from profiles p where p.id = auth.uid() and p.institution_id = institutions.id)
  );

-- user_progress: strictly own rows — this is the gating source of truth
create policy progress_self on user_progress
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- institution_admins can read (not write) progress for their institution's students
create policy progress_admin_read on user_progress
  for select using (
    exists (
      select 1 from profiles admin, profiles student
      where admin.id = auth.uid()
        and admin.role = 'institution_admin'
        and student.id = user_progress.user_id
        and student.institution_id = admin.institution_id
    )
  );

-- subscriptions: individual owner reads own; institution_admin reads their institution's
create policy subscriptions_self on subscriptions
  for select using (auth.uid() = user_id);
create policy subscriptions_admin on subscriptions
  for select using (
    exists (
      select 1 from profiles admin
      where admin.id = auth.uid()
        and admin.role = 'institution_admin'
        and admin.institution_id = subscriptions.institution_id
    )
  );

-- chat: strictly own sessions/messages
create policy chat_sessions_self on chat_sessions
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy chat_messages_self on chat_messages
  for all using (
    exists (select 1 from chat_sessions s where s.id = chat_messages.session_id and s.user_id = auth.uid())
  );

-- topics/challenges: public read (curriculum content, not per-user data)
alter table topics enable row level security;
alter table challenges enable row level security;
create policy topics_public_read on topics for select using (true);
create policy challenges_public_read on challenges for select using (true);

-- seed the 5-topic beginner skill tree
insert into topics (slug, title, order_index, explanation_md) values
  ('qubits-superposition', 'Qubits & Superposition', 1, 'A qubit exists in a weighted combination of |0⟩ and |1⟩ until measured...'),
  ('basic-gates', 'Basic Gates (X / H / Z)', 2, 'Gates rotate a qubit''s state on the Bloch sphere...'),
  ('multi-qubit-circuits', 'Multi-Qubit Circuits', 3, 'Combining qubits multiplies the state space...'),
  ('entanglement', 'Entanglement', 4, 'Entangled qubits share a state that can''t be described independently...'),
  ('deutsch-jozsa', 'Deutsch-Jozsa (simplified)', 5, 'A single query determines constant vs. balanced...');

-- wire prerequisites in order
update topics t2 set prerequisite_id = t1.id
from topics t1
where t1.order_index = t2.order_index - 1;
