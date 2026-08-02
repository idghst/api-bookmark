alter table bookmark.folders
  add column parent_id uuid;

alter table bookmark.folders
  add constraint folders_parent_not_self
    check (parent_id is null or parent_id <> id),
  add constraint folders_parent_owner_fkey
    foreign key (parent_id, user_id)
    references bookmark.folders (id, user_id)
    on delete restrict;

create index folders_owner_parent_position_idx
  on bookmark.folders (user_id, parent_id, position, id);

create or replace function bookmark.enforce_folder_parent_integrity()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, bookmark
as $$
begin
  if new.parent_id is null then
    return new;
  end if;

  if new.parent_id = new.id then
    raise exception using
      errcode = '23514',
      message = 'A folder cannot be its own parent';
  end if;

  if exists (
    with recursive ancestors (id, parent_id) as (
      select folder.id, folder.parent_id
      from bookmark.folders as folder
      where folder.id = new.parent_id
        and folder.user_id = new.user_id

      union

      select parent.id, parent.parent_id
      from bookmark.folders as parent
      join ancestors on parent.id = ancestors.parent_id
      where parent.user_id = new.user_id
    )
    select 1
    from ancestors
    where ancestors.id = new.id
  ) then
    raise exception using
      errcode = '23514',
      message = 'A folder cannot be moved into its descendant';
  end if;

  return new;
end;
$$;

create trigger folders_parent_integrity
before insert or update of parent_id, user_id on bookmark.folders
for each row
execute function bookmark.enforce_folder_parent_integrity();

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
declare
  source_section_ids uuid[];
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

  if exists (
    select 1
    from bookmark.folders as child
    where child.parent_id = p_folder_id
      and child.user_id = p_user_id
  ) then
    raise exception using
      errcode = '23503',
      message = 'Folder has child folders';
  end if;

  select coalesce(array_agg(section.id), array[]::uuid[])
  into source_section_ids
  from bookmark.sections as section
  where section.folder_id = p_folder_id
    and section.user_id = p_user_id;

  if p_destination_folder_id is null then
    update bookmark.items as item
    set folder_id = null,
        section_id = null,
        updated_at = now()
    where item.user_id = p_user_id
      and (
        item.folder_id = p_folder_id
        or item.section_id = any(source_section_ids)
      );
  else
    update bookmark.sections as section
    set folder_id = p_destination_folder_id,
        updated_at = now()
    where section.folder_id = p_folder_id
      and section.user_id = p_user_id;

    update bookmark.items as item
    set folder_id = p_destination_folder_id,
        updated_at = now()
    where item.user_id = p_user_id
      and (
        item.folder_id = p_folder_id
        or item.section_id = any(source_section_ids)
      );
  end if;

  delete from bookmark.folders as folder
  where folder.id = p_folder_id
    and folder.user_id = p_user_id;

  return query select p_folder_id;
end;
$$;

revoke all on function bookmark.delete_folder(uuid, uuid, uuid) from public;
grant execute on function bookmark.delete_folder(uuid, uuid, uuid)
  to authenticated, service_role;
