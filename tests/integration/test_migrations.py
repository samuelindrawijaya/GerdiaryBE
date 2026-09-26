from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

API_DIR = Path(__file__).resolve().parents[2]

USERS_COLUMNS = {
    "id",
    "email",
    "name",
    "password_hash",
    "auth_provider",
    "google_sub",
    "sleep_time",
    "sensitivity_level",
    "goals",
    "currency",
    "timezone",
    "preferences",
    "journal_theme",
    "onboarding_completed_at",
    "created_at",
    "updated_at",
    "deleted_at",
}

FOOD_ENTRIES_COLUMNS = {
    "id",
    "user_id",
    "category_id",
    "consumed_at",
    "meal_type",
    "food_name",
    "emoji",
    "brand",
    "portion",
    "portion_unit",
    "serving_size",
    "preparation_method",
    "food_attributes",
    "source_type",
    "rating",
    "mood_after",
    "energy_level",
    "tags",
    "notes",
    "created_at",
    "updated_at",
    "deleted_at",
}

SYMPTOM_EVENTS_COLUMNS = {
    "id",
    "user_id",
    "food_entry_id",
    "occurred_at",
    "symptom",
    "severity",
    "notes",
    "source",
    "created_at",
    "updated_at",
    "deleted_at",
}


def _run_flask(*arguments: str, env_url: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "FLASK_APP": "wsgi.py",
        "PYTHONPATH": "src",
        "DATABASE_URL": env_url,
        "SECRET_KEY": "migration-test-secret-key-32-characters-min",
        "JWT_SECRET_KEY": "migration-test-jwt-secret-32-characters-min",
        "FRONTEND_ORIGIN": "http://localhost:5173",
        "COOKIE_SECURE": "false",
        "SKIP_DB_TESTS": "",
    }
    executable = sys.executable
    return subprocess.run(
        [executable, "-m", "flask", "db", *arguments],
        cwd=API_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_migration_upgrade_creates_contract_tables_and_downgrades_clean(
    clean_database: Engine,
) -> None:
    upgrade = _run_flask("upgrade", env_url="postgresql+psycopg://postgres:test@localhost:5433/gerdiary_test")
    assert upgrade.returncode == 0, upgrade.stderr

    inspector = inspect(clean_database)
    assert {"users", "categories", "food_entries", "symptom_events", "alembic_version"} <= set(
        inspector.get_table_names()
    )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert USERS_COLUMNS <= user_columns

    users_uniques = {
        unique["name"]
        for unique in inspector.get_unique_constraints("users")
    }
    assert any("email" in name for name in users_uniques)

    category_columns = {column["name"] for column in inspector.get_columns("categories")}
    assert {"id", "user_id", "parent_id", "name", "is_active"} <= category_columns

    food_entry_columns = {column["name"] for column in inspector.get_columns("food_entries")}
    assert FOOD_ENTRIES_COLUMNS <= food_entry_columns

    symptom_event_columns = {
        column["name"] for column in inspector.get_columns("symptom_events")
    }
    assert SYMPTOM_EVENTS_COLUMNS <= symptom_event_columns

    with clean_database.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, password_hash, auth_provider)"
                " VALUES (gen_random_uuid(), 'ayu@example.com', 'hash', 'local')"
            )
        )
        inserted = connection.execute(text("SELECT email FROM users")).scalar_one()
        assert inserted == "ayu@example.com"

    downgrade = _run_flask("downgrade", "base", env_url="postgresql+psycopg://postgres:test@localhost:5433/gerdiary_test")
    assert downgrade.returncode == 0, downgrade.stderr

    after_downgrade = inspect(clean_database)
    assert "users" not in after_downgrade.get_table_names()
