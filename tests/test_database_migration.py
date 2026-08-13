from pathlib import Path

MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260726160000_add_bookmark_resources.sql"
)
FOLDER_HIERARCHY_MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260802195716_folder_hierarchy.sql"
)
SECTION_COLOR_MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260804222840_add_section_color.sql"
)
SECTION_MOVE_MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260805093016_move_section_with_bookmarks.sql"
)
SECTION_MOVE_CONSTRAINT_FIX_MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260814090000_fix_section_move_constraint.sql"
)


def test_resource_migration_creates_expected_tables() -> None:
    sql = MIGRATION.read_text()

    for table in ("folders", "sections", "items"):
        assert f"create table if not exists bookmark.{table}" in sql
        assert f"alter table bookmark.{table} enable row level security" in sql


def test_resource_migration_has_operation_specific_owner_policies() -> None:
    sql = MIGRATION.read_text()

    for table in ("folders", "sections", "items"):
        for operation in ("select", "insert", "update", "delete"):
            assert f"create policy {table}_{operation}_own" in sql
        assert sql.count(f"on bookmark.{table}") >= 5

    assert sql.count("(select auth.uid()) = user_id") == 15
    assert "to authenticated" in sql
    assert "to anon" not in sql


def test_folder_hierarchy_migration_enforces_safe_tree_and_delete_contract() -> None:
    sql = FOLDER_HIERARCHY_MIGRATION.read_text()

    assert "add column parent_id uuid" in sql
    assert "foreign key (parent_id, user_id)" in sql
    assert "on delete restrict" in sql
    assert "with recursive ancestors" in sql
    assert "create trigger folders_parent_integrity" in sql
    assert "create or replace function bookmark.delete_folder(" in sql
    assert "security invoker" in sql
    assert "set search_path = pg_catalog, bookmark" in sql
    assert (
        "revoke all on function bookmark.delete_folder(uuid, uuid, uuid) from public"
        in sql
    )
    assert "to authenticated, service_role" in sql


def test_section_color_migration_adds_nullable_color_column() -> None:
    assert SECTION_COLOR_MIGRATION.read_text() == (
        "alter table bookmark.sections\n  add column color text;\n"
    )


def test_section_move_migration_moves_linked_bookmarks_atomically() -> None:
    sql = SECTION_MOVE_MIGRATION.read_text()

    assert "create or replace function bookmark.move_section(" in sql
    assert "security invoker" in sql
    assert "set search_path = pg_catalog, bookmark" in sql
    assert '"position" integer' in sql
    assert "update bookmark.sections as section" in sql
    assert "update bookmark.items as item" in sql
    assert "where item.section_id = p_section_id" in sql
    assert "set folder_id = p_destination_folder_id" in sql
    assert "name = case when p_update_name then p_name else section.name end" in sql
    assert "color = case when p_update_color then p_color else section.color end" in sql
    assert "coalesce(max(section.position) + 1, 0)" in sql
    assert (
        "revoke all on function bookmark.move_section(\n"
        "  uuid, uuid, uuid, text, text, boolean, boolean\n"
        ") from public" in sql
    )
    assert "to authenticated, service_role" in sql


def test_section_move_constraint_fix_defers_linked_bookmark_foreign_key() -> None:
    sql = SECTION_MOVE_CONSTRAINT_FIX_MIGRATION.read_text()

    assert (
        "alter constraint items_section_owner_fkey deferrable initially immediate"
        in sql
    )
    assert "set constraints items_section_owner_fkey deferred" in sql
    assert "create or replace function bookmark.move_section(" in sql
    assert '"position" integer' in sql
    assert "security invoker" in sql
    assert "to authenticated, service_role" in sql
