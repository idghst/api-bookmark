grant select, insert, update, delete
  on bookmark.folder_sections
  to service_role;

notify pgrst, 'reload schema';
