import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_config_uses_fastapi_fluid_function() -> None:
    config = json.loads((ROOT / "vercel.json").read_text())

    assert config["framework"] == "fastapi"
    assert config["fluid"] is True
    assert config["functions"] == {"app/main.py": {"maxDuration": 30}}


def test_vercelignore_excludes_non_runtime_content_without_hiding_app() -> None:
    rules = {
        line.strip()
        for line in (ROOT / ".vercelignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert {
        ".env*",
        ".git/",
        ".venv/",
        "docs/",
        "supabase/",
        "tests/",
    } <= rules
    assert "/*" not in rules
    assert not any(rule.lstrip("!/").startswith("app") for rule in rules)


def test_readme_requires_preview_source_deployment() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "vercel build --target=preview" in readme
    assert "vercel deploy --target=preview" in readme
    assert "vercel deploy --prebuilt" not in readme
