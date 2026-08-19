-- 계층을 반전한다. 이전: folders(parent_id) > sections(folder_id) > items(section_id).
-- 이후: sections > folders(section_id) > items(folder_id).
-- 하위 폴더와 북마크의 섹션 소속은 제거하고, 섹션은 폴더를 묶는 최상위 그룹이 된다.

-- 되돌릴 근거를 남긴다. grant/policy가 없어 PostgREST로는 노출되지 않는다.
create table if not exists bookmark._hierarchy_backup_20260820 (
  captured_at timestamptz not null default now(),
  folders jsonb not null,
  sections jsonb not null,
  items jsonb not null
);

alter table bookmark._hierarchy_backup_20260820 enable row level security;

insert into bookmark._hierarchy_backup_20260820 (folders, sections, items)
select
  (
    select coalesce(jsonb_agg(to_jsonb(folder)), '[]'::jsonb)
    from bookmark.folders as folder
  ),
  (
    select coalesce(jsonb_agg(to_jsonb(section)), '[]'::jsonb)
    from bookmark.sections as section
  ),
  (
    select coalesce(
      jsonb_agg(jsonb_build_object(
        'id', item.id,
        'user_id', item.user_id,
        'folder_id', item.folder_id,
        'section_id', item.section_id
      )),
      '[]'::jsonb
    )
    from bookmark.items as item
  );

-- 기존 섹션은 폴더의 하위 그룹이라 반전 후 의미가 없다. 구조를 비우고 다시 만든다.
delete from bookmark.sections;

drop function if exists bookmark.move_section(uuid, uuid, uuid, text, text, boolean, boolean);

drop trigger if exists folders_parent_integrity on bookmark.folders;
drop function if exists bookmark.enforce_folder_parent_integrity();

-- 컬럼을 지우면 그 컬럼을 쓰는 FK·check·unique·인덱스도 함께 사라진다.
drop index if exists bookmark.items_owner_section_position_idx;

alter table bookmark.items
  drop column if exists section_id;

drop index if exists bookmark.sections_owner_folder_position_idx;

alter table bookmark.sections
  drop column if exists folder_id;

-- folders가 (section_id, user_id)로 참조하려면 sections에 같은 조합의 unique가 있어야 한다.
do $$
begin
  if not exists (
    select 1
    from pg_constraint as con
    join pg_class as tbl on tbl.oid = con.conrelid
    join pg_namespace as ns on ns.oid = tbl.relnamespace
    where ns.nspname = 'bookmark'
      and tbl.relname = 'sections'
      and con.contype = 'u'
      and array_length(con.conkey, 1) = 2
      and (
        select count(*)
        from unnest(con.conkey) as key
        join pg_attribute as att
          on att.attrelid = tbl.oid and att.attnum = key
        where att.attname in ('id', 'user_id')
      ) = 2
  ) then
    alter table bookmark.sections
      add constraint sections_id_user_key unique (id, user_id);
  end if;
end $$;

create index if not exists sections_owner_position_idx
  on bookmark.sections (user_id, position);

drop index if exists bookmark.folders_owner_parent_position_idx;

alter table bookmark.folders
  drop column if exists parent_id;

alter table bookmark.folders
  add column if not exists section_id uuid;

alter table bookmark.folders
  drop constraint if exists folders_section_owner_fkey;

alter table bookmark.folders
  add constraint folders_section_owner_fkey
    foreign key (section_id, user_id)
    references bookmark.sections (id, user_id)
    on delete set null (section_id);

create index if not exists folders_owner_section_position_idx
  on bookmark.folders (user_id, section_id, position, id);

-- 하위 폴더가 없어졌으므로 자식 검사와 섹션 재배치를 뺀다.
create or replace function bookmark.delete_folder(
  p_folder_id uuid,
  p_destination_folder_id uuid,
  p_user_id uuid
)
returns table (id uuid)
language plpgsql
security invoker
set search_path = pg_catalog, bookmark
as $$
begin
  if p_user_id is null then
    raise exception using errcode = '22004', message = 'A folder owner is required';
  end if;

  if (select auth.uid()) is not null
    and (select auth.uid()) <> p_user_id then
    raise exception using errcode = '42501', message = 'Folder owner does not match caller';
  end if;

  perform 1
  from bookmark.folders as folder
  where folder.id = p_folder_id
    and folder.user_id = p_user_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'Folder not found';
  end if;

  if p_destination_folder_id = p_folder_id then
    raise exception using
      errcode = '23514',
      message = 'A folder cannot be its own deletion destination';
  end if;

  if p_destination_folder_id is not null and not exists (
    select 1
    from bookmark.folders as destination
    where destination.id = p_destination_folder_id
      and destination.user_id = p_user_id
  ) then
    raise exception using
      errcode = '23503',
      message = 'Deletion destination folder not found';
  end if;

  update bookmark.items as item
  set folder_id = p_destination_folder_id,
      updated_at = now()
  where item.user_id = p_user_id
    and item.folder_id = p_folder_id;

  delete from bookmark.folders as folder
  where folder.id = p_folder_id
    and folder.user_id = p_user_id;

  return query select p_folder_id;
end;
$$;

revoke all on function bookmark.delete_folder(uuid, uuid, uuid) from public;
grant execute on function bookmark.delete_folder(uuid, uuid, uuid)
  to authenticated, service_role;
