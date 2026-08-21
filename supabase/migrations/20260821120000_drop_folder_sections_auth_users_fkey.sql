-- folders/items는 auth.users FK가 없다. 운영 user_id가 auth.users에 없을 수 있다.
-- 소유 정합은 (folder_id, user_id) → folders 로 유지한다.

alter table bookmark.folder_sections
  drop constraint folder_sections_user_id_fkey;
