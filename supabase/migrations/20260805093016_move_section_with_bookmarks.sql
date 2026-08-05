create or replace function bookmark.move_section(
  p_section_id uuid,
  p_destination_folder_id uuid,
  p_user_id uuid,
  p_name text,
  p_color text,
  p_update_name boolean,
  p_update_color boolean
)
returns table (
  id uuid,
  name text,
  color text,
  folder_id uuid,
  position integer,
  user_id uuid
)
language plpgsql
security invoker
set search_path = pg_catalog, bookmark
as $$
declare
  source_folder_id uuid;
  target_position integer;
  moved_section bookmark.sections%rowtype;
begin
  if p_user_id is null then
    raise exception using errcode = '22004', message = 'A section owner is required';
  end if;

  if p_destination_folder_id is null then
    raise exception using errcode = '22004', message = 'A destination folder is required';
  end if;

  if (select auth.uid()) is not null
    and (select auth.uid()) <> p_user_id then
    raise exception using errcode = '42501', message = 'Section owner does not match caller';
  end if;

  select section.folder_id, section.position
  into source_folder_id, target_position
  from bookmark.sections as section
  where section.id = p_section_id
    and section.user_id = p_user_id
  for update;

  if not found then
    raise exception using errcode = 'P0002', message = 'Section not found';
  end if;

  if not exists (
    select 1
    from bookmark.folders as folder
    where folder.id = p_destination_folder_id
      and folder.user_id = p_user_id
  ) then
    raise exception using
      errcode = '23503',
      message = 'Destination folder not found';
  end if;

  if source_folder_id <> p_destination_folder_id then
    select coalesce(max(section.position) + 1, 0)
    into target_position
    from bookmark.sections as section
    where section.folder_id = p_destination_folder_id
      and section.user_id = p_user_id;
  end if;

  update bookmark.sections as section
  set name = case when p_update_name then p_name else section.name end,
      color = case when p_update_color then p_color else section.color end,
      folder_id = p_destination_folder_id,
      position = target_position,
      updated_at = now()
  where section.id = p_section_id
    and section.user_id = p_user_id
  returning section.* into moved_section;

  update bookmark.items as item
  set folder_id = p_destination_folder_id,
      updated_at = now()
  where item.section_id = p_section_id
    and item.user_id = p_user_id;

  return query
  select
    moved_section.id,
    moved_section.name,
    moved_section.color,
    moved_section.folder_id,
    moved_section.position,
    moved_section.user_id;
end;
$$;

revoke all on function bookmark.move_section(
  uuid, uuid, uuid, text, text, boolean, boolean
) from public;
grant execute on function bookmark.move_section(
  uuid, uuid, uuid, text, text, boolean, boolean
)
  to authenticated, service_role;
