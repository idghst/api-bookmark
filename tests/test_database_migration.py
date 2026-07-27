from pathlib import Path

MIGRATION = (
    Path(__file__).parent.parent
    / "supabase"
    / "migrations"
    / "20260726160000_add_bookmark_resources.sql"
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
