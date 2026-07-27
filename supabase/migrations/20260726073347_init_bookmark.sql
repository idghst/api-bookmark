create schema if not exists bookmark;
grant usage on schema bookmark to anon, authenticated, service_role;
alter default privileges in schema bookmark
  grant all on tables to service_role;
alter default privileges in schema bookmark
  grant all on sequences to service_role;
alter default privileges in schema bookmark
  grant execute on routines to service_role;
