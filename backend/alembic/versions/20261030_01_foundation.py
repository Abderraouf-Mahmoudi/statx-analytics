"""Add the local-first organization and roster foundation.

Revision ID: 20261030_01
Revises:
Create Date: 2026-10-30
"""

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20261030_01"
down_revision = None
branch_labels = None
depends_on = None


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_id() -> str:
    return str(uuid4())


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def add_columns(table: str, columns: Iterable[sa.Column]) -> None:
    existing = column_names(table)
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    # SQLite cannot add named foreign-key constraints after the fact. Batch
    # mode rebuilds only the affected table while retaining every legacy row.
    with op.batch_alter_table(table, recreate="always") as batch_op:
        for column in missing:
            batch_op.add_column(column)


def ensure_unique_public_id_index(table: str) -> None:
    name = f"ux_{table}_public_id"
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, ["public_id"], unique=True)


def ensure_index(table: str, column: str) -> None:
    name = f"ix_{table}_{column}"
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, [column], unique=False)


def create_foundation_tables() -> None:
    existing = table_names()
    if "organizations" not in existing:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("country_code", sa.String(2), nullable=True),
            sa.Column("default_locale", sa.String(10), nullable=False, server_default="fr"),
            sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_organizations_public_id"),
        )
    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("default_locale", sa.String(10), nullable=False, server_default="fr"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_users_public_id"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
    if "memberships" not in existing:
        op.create_table(
            "memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_memberships_public_id"),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
            sa.CheckConstraint(
                "role IN ('admin', 'analyst', 'coach', 'viewer')", name="ck_membership_role"
            ),
        )
    if "seasons" not in existing:
        op.create_table(
            "seasons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_seasons_public_id"),
            sa.UniqueConstraint("organization_id", "name", name="uq_season_org_name"),
        )


def create_or_extend_teams() -> None:
    if "teams" not in table_names():
        op.create_table(
            "teams",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("logo_url", sa.String(500), nullable=True),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("gender", sa.String(30), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("name", name="uq_teams_name"),
            sa.UniqueConstraint("public_id", name="uq_teams_public_id"),
        )
    else:
        add_columns(
            "teams",
            [
                sa.Column("public_id", sa.String(36), nullable=True),
                sa.Column(
                    "organization_id",
                    sa.Integer(),
                    sa.ForeignKey("organizations.id", name="fk_teams_organization_id"),
                    nullable=True,
                ),
                sa.Column("category", sa.String(50), nullable=True),
                sa.Column("gender", sa.String(30), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            ],
        )
    if "team_seasons" not in table_names():
        op.create_table(
            "team_seasons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_team_seasons_public_id"),
            sa.UniqueConstraint("team_id", "season_id", name="uq_team_season"),
        )


def create_or_extend_players() -> None:
    if "players" not in table_names():
        op.create_table(
            "players",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("first_name", sa.String(80), nullable=True),
            sa.Column("last_name", sa.String(80), nullable=True),
            sa.Column("birth_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("jersey_number", sa.Integer(), nullable=True),
            sa.Column("position", sa.String(50), nullable=False),
            sa.Column("preferred_foot", sa.String(20), nullable=True),
            sa.UniqueConstraint("public_id", name="uq_players_public_id"),
            sa.CheckConstraint(
                "jersey_number >= 0 AND jersey_number <= 99", name="ck_player_jersey"
            ),
        )
    else:
        add_columns(
            "players",
            [
                sa.Column("public_id", sa.String(36), nullable=True),
                sa.Column(
                    "organization_id",
                    sa.Integer(),
                    sa.ForeignKey("organizations.id", name="fk_players_organization_id"),
                    nullable=True,
                ),
                sa.Column("first_name", sa.String(80), nullable=True),
                sa.Column("last_name", sa.String(80), nullable=True),
                sa.Column("birth_date", sa.Date(), nullable=True),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            ],
        )
    if "player_registrations" not in table_names():
        op.create_table(
            "player_registrations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
            sa.Column("shirt_number", sa.Integer(), nullable=True),
            sa.Column("position", sa.String(50), nullable=True),
            sa.Column("preferred_foot", sa.String(20), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_player_registrations_public_id"),
            sa.UniqueConstraint("player_id", "team_id", "season_id", name="uq_registration_roster"),
            sa.CheckConstraint(
                "shirt_number IS NULL OR (shirt_number >= 0 AND shirt_number <= 99)",
                name="ck_registration_shirt",
            ),
        )
    if "consents" not in table_names():
        op.create_table(
            "consents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("consent_type", sa.String(40), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("document_sha256", sa.String(64), nullable=True),
            sa.Column("subject_is_minor", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("guardian_name", sa.String(160), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evidence_note", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_consents_public_id"),
        )


def create_or_extend_match_data() -> None:
    if "matches" not in table_names():
        op.create_table(
            "matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=True),
            sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("match_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("home_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("away_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("competition", sa.String(120), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.UniqueConstraint("public_id", name="uq_matches_public_id"),
        )
    else:
        add_columns(
            "matches",
            [
                sa.Column("public_id", sa.String(36), nullable=True),
                sa.Column(
                    "season_id",
                    sa.Integer(),
                    sa.ForeignKey("seasons.id", name="fk_matches_season_id"),
                    nullable=True,
                ),
                sa.Column("status", sa.String(20), nullable=True),
            ],
        )
    if "events" not in table_names():
        op.create_table(
            "events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("minute", sa.Integer(), nullable=False),
            sa.Column("second", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("type", sa.String(20), nullable=False),
            sa.Column("x_start", sa.Float(), nullable=False),
            sa.Column("y_start", sa.Float(), nullable=False),
            sa.Column("x_end", sa.Float(), nullable=True),
            sa.Column("y_end", sa.Float(), nullable=True),
            sa.Column("outcome", sa.String(50), nullable=True),
            sa.Column("xg_value", sa.Float(), nullable=True),
            sa.UniqueConstraint("public_id", name="uq_events_public_id"),
            sa.CheckConstraint("minute >= 0 AND second >= 0 AND second <= 59", name="ck_event_time"),
            sa.CheckConstraint("type IN ('shot', 'pass', 'recovery')", name="ck_event_type"),
            sa.CheckConstraint("x_start >= 0 AND x_start <= 120", name="ck_event_x_start"),
            sa.CheckConstraint("y_start >= 0 AND y_start <= 80", name="ck_event_y_start"),
            sa.CheckConstraint(
                "x_end IS NULL OR (x_end >= 0 AND x_end <= 120)", name="ck_event_x_end"
            ),
            sa.CheckConstraint(
                "y_end IS NULL OR (y_end >= 0 AND y_end <= 80)", name="ck_event_y_end"
            ),
            sa.CheckConstraint(
                "xg_value IS NULL OR (xg_value >= 0 AND xg_value <= 1)", name="ck_event_xg"
            ),
        )
    else:
        add_columns("events", [sa.Column("public_id", sa.String(36), nullable=True)])
    if "tracking_points" not in table_names():
        op.create_table(
            "tracking_points",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("timestamp_seconds", sa.Float(), nullable=False),
            sa.Column("x_coord", sa.Float(), nullable=False),
            sa.Column("y_coord", sa.Float(), nullable=False),
            sa.Column("speed_kmh", sa.Float(), nullable=False, server_default="0"),
            sa.UniqueConstraint(
                "match_id", "player_id", "timestamp_seconds", name="uq_tracking_match_player_timestamp"
            ),
            sa.CheckConstraint("timestamp_seconds >= 0", name="ck_tracking_timestamp"),
            sa.CheckConstraint("x_coord >= 0 AND x_coord <= 105", name="ck_tracking_x"),
            sa.CheckConstraint("y_coord >= 0 AND y_coord <= 68", name="ck_tracking_y"),
            sa.CheckConstraint("speed_kmh >= 0", name="ck_tracking_speed"),
        )


def create_platform_tables() -> None:
    if "system_state" not in table_names():
        op.create_table(
            "system_state",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bootstrapped", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("installation_id", sa.String(36), nullable=False),
            sa.Column("schema_version", sa.String(40), nullable=False, server_default="foundation"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("installation_id", name="uq_system_state_installation"),
        )
        op.get_bind().execute(
            sa.text(
                "INSERT INTO system_state "
                "(id, bootstrapped, installation_id, schema_version, updated_at) "
                "VALUES (1, 0, :installation_id, 'foundation', :updated_at)"
            ),
            {"installation_id": public_id(), "updated_at": now_text()},
        )
    if "audit_logs" not in table_names():
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(36), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(80), nullable=False),
            sa.Column("entity_public_id", sa.String(36), nullable=False),
            sa.Column("before", sa.JSON(), nullable=True),
            sa.Column("after", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("public_id", name="uq_audit_logs_public_id"),
        )


def backfill_legacy_data(had_legacy_rows: bool) -> None:
    if not had_legacy_rows:
        return
    bind = op.get_bind()
    timestamp = now_text()
    organization_result = bind.execute(
        sa.text(
            "INSERT INTO organizations "
            "(public_id, name, country_code, default_locale, timezone, created_at, updated_at) "
            "VALUES (:public_id, 'Imported organization', NULL, 'fr', 'UTC', :created_at, :updated_at)"
        ),
        {"public_id": public_id(), "created_at": timestamp, "updated_at": timestamp},
    )
    organization_id = organization_result.lastrowid
    season_result = bind.execute(
        sa.text(
            "INSERT INTO seasons (public_id, organization_id, name, start_date, end_date, created_at) "
            "VALUES (:public_id, :organization_id, 'Imported season', NULL, NULL, :created_at)"
        ),
        {"public_id": public_id(), "organization_id": organization_id, "created_at": timestamp},
    )
    season_id = season_result.lastrowid

    for row in bind.execute(sa.text("SELECT id FROM teams ORDER BY id")).mappings():
        bind.execute(
            sa.text(
                "UPDATE teams SET public_id=:public_id, organization_id=:organization_id, "
                "updated_at=COALESCE(updated_at, created_at, :updated_at) WHERE id=:id"
            ),
            {
                "id": row["id"],
                "public_id": public_id(),
                "organization_id": organization_id,
                "updated_at": timestamp,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO team_seasons (public_id, team_id, season_id, created_at) "
                "VALUES (:public_id, :team_id, :season_id, :created_at)"
            ),
            {
                "public_id": public_id(),
                "team_id": row["id"],
                "season_id": season_id,
                "created_at": timestamp,
            },
        )

    for row in bind.execute(
        sa.text(
            "SELECT id, team_id, name, jersey_number, position, preferred_foot FROM players ORDER BY id"
        )
    ).mappings():
        name_parts = row["name"].strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else row["name"]
        last_name = name_parts[1] if len(name_parts) == 2 else ""
        bind.execute(
            sa.text(
                "UPDATE players SET public_id=:public_id, organization_id=:organization_id, "
                "first_name=:first_name, last_name=:last_name, "
                "created_at=:created_at, updated_at=:updated_at WHERE id=:id"
            ),
            {
                "id": row["id"],
                "public_id": public_id(),
                "organization_id": organization_id,
                "first_name": first_name,
                "last_name": last_name,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO player_registrations "
                "(public_id, player_id, team_id, season_id, shirt_number, position, preferred_foot, "
                "start_date, end_date, status, created_at) "
                "VALUES (:public_id, :player_id, :team_id, :season_id, :shirt_number, :position, "
                ":preferred_foot, NULL, NULL, 'active', :created_at)"
            ),
            {
                "public_id": public_id(),
                "player_id": row["id"],
                "team_id": row["team_id"],
                "season_id": season_id,
                "shirt_number": row["jersey_number"],
                "position": row["position"],
                "preferred_foot": row["preferred_foot"],
                "created_at": timestamp,
            },
        )

    for row in bind.execute(sa.text("SELECT id FROM matches ORDER BY id")).mappings():
        bind.execute(
            sa.text(
                "UPDATE matches SET public_id=:public_id, season_id=:season_id, status='completed' "
                "WHERE id=:id"
            ),
            {"id": row["id"], "public_id": public_id(), "season_id": season_id},
        )
    for row in bind.execute(sa.text("SELECT id FROM events ORDER BY id")).mappings():
        bind.execute(
            sa.text("UPDATE events SET public_id=:public_id WHERE id=:id"),
            {"id": row["id"], "public_id": public_id()},
        )


def upgrade() -> None:
    bind = op.get_bind()
    initial_tables = table_names()
    had_legacy_rows = any(
        table in initial_tables
        and bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one() > 0
        for table in ("teams", "players", "matches", "events", "tracking_points")
    )

    create_foundation_tables()
    create_or_extend_teams()
    create_or_extend_players()
    create_or_extend_match_data()
    create_platform_tables()
    backfill_legacy_data(had_legacy_rows)

    # Tables extended from the prototype did not have a public UUID
    # constraint. A unique index adds that guarantee without dropping data.
    for table in (
        "organizations",
        "users",
        "memberships",
        "seasons",
        "teams",
        "team_seasons",
        "players",
        "player_registrations",
        "consents",
        "matches",
        "events",
        "audit_logs",
    ):
        if table in initial_tables:
            ensure_unique_public_id_index(table)

    for table, column in (
        ("organizations", "name"),
        ("memberships", "user_id"),
        ("memberships", "organization_id"),
        ("seasons", "organization_id"),
        ("teams", "organization_id"),
        ("team_seasons", "team_id"),
        ("team_seasons", "season_id"),
        ("players", "organization_id"),
        ("players", "team_id"),
        ("players", "name"),
        ("player_registrations", "player_id"),
        ("player_registrations", "team_id"),
        ("player_registrations", "season_id"),
        ("consents", "player_id"),
        ("matches", "season_id"),
        ("matches", "home_team_id"),
        ("matches", "away_team_id"),
        ("matches", "match_date"),
        ("events", "match_id"),
        ("events", "player_id"),
        ("events", "type"),
        ("tracking_points", "match_id"),
        ("tracking_points", "player_id"),
        ("audit_logs", "actor_id"),
        ("audit_logs", "organization_id"),
        ("audit_logs", "action"),
        ("audit_logs", "entity_type"),
        ("audit_logs", "entity_public_id"),
        ("audit_logs", "created_at"),
    ):
        ensure_index(table, column)


def downgrade() -> None:
    raise RuntimeError("The legacy-safe foundation migration is intentionally irreversible")
