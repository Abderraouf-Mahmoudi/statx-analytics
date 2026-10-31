"""Add provider synchronization and player media persistence.

Revision ID: 20261031_02
Revises: 20261030_01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261031_02"
down_revision: str | None = "20261030_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("seasons") as batch:
        batch.add_column(sa.Column("provider", sa.String(40), nullable=True))
        batch.add_column(sa.Column("competition_provider_id", sa.String(80), nullable=True))
        batch.add_column(sa.Column("season_year", sa.Integer(), nullable=True))

    with op.batch_alter_table("teams") as batch:
        batch.add_column(sa.Column("source", sa.String(24), nullable=False, server_default="manual"))
        batch.add_column(sa.Column("provider", sa.String(40), nullable=True))
        batch.add_column(sa.Column("provider_id", sa.String(80), nullable=True))
        batch.add_column(sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("logo_source_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("logo_local_path", sa.String(500), nullable=True))
        batch.create_unique_constraint("uq_teams_org_provider_id", ["organization_id", "provider", "provider_id"])

    with op.batch_alter_table("organizations") as batch:
        batch.add_column(sa.Column("primary_team_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_organizations_primary_team_id", "teams", ["primary_team_id"], ["id"])
        batch.create_index("ix_organizations_primary_team_id", ["primary_team_id"])

    with op.batch_alter_table("players") as batch:
        batch.add_column(sa.Column("source", sa.String(24), nullable=False, server_default="manual"))
        batch.add_column(sa.Column("provider", sa.String(40), nullable=True))
        batch.add_column(sa.Column("provider_id", sa.String(80), nullable=True))
        batch.add_column(sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("nationality", sa.String(80), nullable=True))
        batch.add_column(sa.Column("height_cm", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("weight_kg", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("provider_photo_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("local_override", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("provider_absent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_unique_constraint("uq_players_org_provider_id", ["organization_id", "provider", "provider_id"])

    with op.batch_alter_table("matches") as batch:
        batch.add_column(sa.Column("provider", sa.String(40), nullable=True))
        batch.add_column(sa.Column("provider_id", sa.String(80), nullable=True))
        batch.add_column(sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint("uq_matches_provider_id", ["provider", "provider_id"])

    op.create_table(
        "provider_cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(160), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "cache_key", name="uq_provider_cache_key"),
    )
    op.create_index("ix_provider_cache_entries_provider", "provider_cache_entries", ["provider"])
    op.create_index("ix_provider_cache_entries_expires_at", "provider_cache_entries", ["expires_at"])

    op.create_table(
        "provider_quota_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("quota_date", sa.Date(), nullable=False),
        sa.Column("calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_reported", sa.Integer(), nullable=True),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "quota_date", name="uq_provider_quota_day"),
    )
    op.create_index("ix_provider_quota_days_provider", "provider_quota_days", ["provider"])

    op.create_table(
        "provider_sync_leases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("owner_token", sa.String(64), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "provider", name="uq_provider_sync_lease"),
    )
    op.create_index("ix_provider_sync_leases_organization_id", "provider_sync_leases", ["organization_id"])
    op.create_index("ix_provider_sync_leases_expires_at", "provider_sync_leases", ["expires_at"])

    op.create_table(
        "provider_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_quota", sa.Integer(), nullable=True),
        sa.Column("request_json", sa.JSON(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("organization_id", "team_id", "provider", "status"):
        op.create_index(f"ix_provider_sync_runs_{column}", "provider_sync_runs", [column])

    op.create_table(
        "provider_standing_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "team_id", "season_id", "provider", name="uq_provider_standing"),
    )
    for column in ("organization_id", "team_id", "season_id"):
        op.create_index(f"ix_provider_standing_snapshots_{column}", "provider_standing_snapshots", [column])

    op.create_table(
        "player_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("original_path", sa.String(500), nullable=True),
        sa.Column("cutout_path", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("processing_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("rights_status", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('camera','gallery','api_football')", name="ck_player_photo_source"),
        sa.CheckConstraint("processing_status IN ('pending','processing','ready','failed')", name="ck_player_photo_status"),
        sa.CheckConstraint("rights_status IN ('unknown','club_authorized','provider_identification_only')", name="ck_player_photo_rights"),
    )
    op.create_index("ix_player_photos_player_id", "player_photos", ["player_id"])
    op.create_index("ix_player_photos_sha256", "player_photos", ["sha256"])
    op.create_index("ix_player_photos_processing_status", "player_photos", ["processing_status"])


def downgrade() -> None:
    raise RuntimeError("Provider/media migration is intentionally irreversible")
