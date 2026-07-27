create table if not exists bookmark.folders (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  color text,
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, user_id)
);

create table if not exists bookmark.sections (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  folder_id uuid not null,
  name text not null,
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, user_id),
  foreign key (folder_id, user_id)
    references bookmark.folders (id, user_id) on delete cascade
);

create table if not exists bookmark.items (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  folder_id uuid,
  section_id uuid,
  title text not null,
  url text not null,
  description text,
  is_favorite boolean not null default false,
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (folder_id, user_id)
    references bookmark.folders (id, user_id) on delete set null (folder_id),
  foreign key (section_id, user_id)
    references bookmark.sections (id, user_id) on delete set null (section_id)
);

create index if not exists folders_owner_position_idx
  on bookmark.folders (user_id, position);
create index if not exists sections_owner_folder_position_idx
  on bookmark.sections (user_id, folder_id, position);
create index if not exists items_owner_folder_position_idx
  on bookmark.items (user_id, folder_id, position);
create index if not exists items_owner_section_position_idx
  on bookmark.items (user_id, section_id, position);

alter table bookmark.folders enable row level security;
alter table bookmark.sections enable row level security;
alter table bookmark.items enable row level security;

grant select, insert, update, delete
  on bookmark.folders, bookmark.sections, bookmark.items
  to authenticated;

create policy folders_select_own on bookmark.folders
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy folders_insert_own on bookmark.folders
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy folders_update_own on bookmark.folders
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy folders_delete_own on bookmark.folders
  for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy sections_select_own on bookmark.sections
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy sections_insert_own on bookmark.sections
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy sections_update_own on bookmark.sections
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy sections_delete_own on bookmark.sections
  for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy items_select_own on bookmark.items
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy items_insert_own on bookmark.items
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy items_update_own on bookmark.items
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy items_delete_own on bookmark.items
  for delete to authenticated
  using ((select auth.uid()) = user_id);
