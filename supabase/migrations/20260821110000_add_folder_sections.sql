-- 폴더 안 북마크 그룹. 사이드바 최상위 bookmark.sections 와 겸용하지 않는다.
-- 기존 items/folders/sections 행은 지우지 않는다.

create table bookmark.folder_sections (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  folder_id uuid not null,
  name text not null,
  color text,
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, user_id),
  unique (id, folder_id, user_id),
  foreign key (folder_id, user_id)
    references bookmark.folders (id, user_id) on delete cascade
);

create index folder_sections_owner_folder_position_idx
  on bookmark.folder_sections (user_id, folder_id, position, id);

alter table bookmark.items
  add column folder_section_id uuid;

alter table bookmark.items
  add constraint items_folder_section_same_folder_fkey
    foreign key (folder_section_id, folder_id, user_id)
    references bookmark.folder_sections (id, folder_id, user_id)
    on delete set null (folder_section_id);

alter table bookmark.items
  add constraint items_folder_section_requires_folder
    check (folder_section_id is null or folder_id is not null);

create index items_owner_folder_section_position_idx
  on bookmark.items (user_id, folder_id, folder_section_id, position, id);

alter table bookmark.folder_sections enable row level security;

grant select, insert, update, delete
  on bookmark.folder_sections
  to authenticated;

create policy folder_sections_select_own on bookmark.folder_sections
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy folder_sections_insert_own on bookmark.folder_sections
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy folder_sections_update_own on bookmark.folder_sections
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy folder_sections_delete_own on bookmark.folder_sections
  for delete to authenticated
  using ((select auth.uid()) = user_id);

create or replace function bookmark.clear_folder_section_on_folder_change()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, bookmark
as $$
begin
  if new.folder_id is distinct from old.folder_id
    and new.folder_section_id is not distinct from old.folder_section_id then
    new.folder_section_id := null;
  end if;
  return new;
end;
$$;

create trigger items_clear_folder_section_on_folder_change
  before update of folder_id on bookmark.items
  for each row
  execute function bookmark.clear_folder_section_on_folder_change();

create or replace function bookmark.move_bookmark_within_folder(
  p_item_id uuid,
  p_folder_section_id uuid,
  p_position integer,
  p_user_id uuid
)
returns table (
  id uuid,
  folder_section_id uuid,
  "position" integer
)
language plpgsql
security invoker
set search_path = pg_catalog, bookmark
as $$
declare
  source bookmark.items%rowtype;
  target_position integer;
begin
  if p_user_id is null then
    raise exception using errcode = '22004', message = 'A bookmark owner is required';
  end if;

  if (select auth.uid()) is not null
    and (select auth.uid()) <> p_user_id then
    raise exception using errcode = '42501', message = 'Bookmark owner does not match caller';
  end if;

  select item.*
  into source
  from bookmark.items as item
  where item.id = p_item_id
    and item.user_id = p_user_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'Bookmark not found';
  end if;

  if p_folder_section_id is not null then
    if exists (
      select 1
      from bookmark.folder_sections as destination
      where destination.id = p_folder_section_id
        and destination.user_id = p_user_id
        and destination.folder_id <> source.folder_id
    ) then
      raise exception using
        errcode = '23514',
        message = 'Bookmark section must stay in the same folder';
    end if;

    if not exists (
      select 1
      from bookmark.folder_sections as destination
      where destination.id = p_folder_section_id
        and destination.user_id = p_user_id
        and destination.folder_id = source.folder_id
    ) then
      raise exception using errcode = 'P0002', message = 'Folder section not found';
    end if;
  end if;

  target_position := p_position;
  if target_position is null then
    select coalesce(max(item.position) + 1, 0)
    into target_position
    from bookmark.items as item
    where item.user_id = p_user_id
      and item.folder_id is not distinct from source.folder_id
      and item.folder_section_id is not distinct from p_folder_section_id
      and item.id <> p_item_id;
  end if;

  update bookmark.items as item
  set folder_section_id = p_folder_section_id,
      position = target_position,
      updated_at = now()
  where item.id = p_item_id
    and item.user_id = p_user_id;

  return query
  select item.id, item.folder_section_id, item.position
  from bookmark.items as item
  where item.id = p_item_id
    and item.user_id = p_user_id;
end;
$$;

revoke all on function bookmark.move_bookmark_within_folder(uuid, uuid, integer, uuid) from public;
grant execute on function bookmark.move_bookmark_within_folder(uuid, uuid, integer, uuid)
  to authenticated, service_role;
