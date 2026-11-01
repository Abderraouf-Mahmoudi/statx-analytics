"""Add account function, player enrichment, and sync-stage persistence.

Revision ID: 20261101_03
Revises: 20261031_02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261101_03"
down_revision: str | None = "20261031_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("job_title", sa.String(24), nullable=False, server_default="other")
        )
        batch.create_check_constraint(
            "ck_user_job_title",
            "job_title IN ('director','coach','analyst','scout','medical','media','other')",
        )

    with op.batch_alter_table("players") as batch:
        batch.add_column(sa.Column("display_name", sa.String(160), nullable=True))
        batch.add_column(sa.Column("birth_place", sa.String(120), nullable=True))
        batch.add_column(sa.Column("birth_country", sa.String(80), nullable=True))
        batch.add_column(
            sa.Column("primary_position", sa.String(10), nullable=False, server_default="OTHER")
        )
        batch.add_column(
            sa.Column(
                "secondary_positions",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch.add_column(
            sa.Column(
                "player_field_overrides",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.create_check_constraint(
            "ck_player_primary_position",
            "primary_position IN ('GK','RB','CB','LB','DM','CM','AM','RW','LW','ST','OTHER')",
        )

    op.execute(
        sa.text(
            "UPDATE players SET display_name=COALESCE(NULLIF(name, ''), "
            "TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))), "
            "primary_position=CASE WHEN UPPER(position) IN "
            "('GK','RB','CB','LB','DM','CM','AM','RW','LW','ST') "
            "THEN UPPER(position) ELSE 'OTHER' END"
        )
    )

    op.create_table(
        "player_season_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("statistics_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "player_id",
            "team_id",
            "season_id",
            "provider",
            name="uq_player_season_snapshot",
        ),
    )
    for column in ("organization_id", "player_id", "team_id", "season_id"):
        op.create_index(
            f"ix_player_season_snapshots_{column}", "player_season_snapshots", [column]
        )

    op.create_table(
        "provider_sync_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sync_run_id", sa.Integer(), sa.ForeignKey("provider_sync_runs.id"), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("sync_run_id", "name", name="uq_provider_sync_stage"),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','skipped','failed')",
            name="ck_provider_sync_stage_status",
        ),
    )
    op.create_index("ix_provider_sync_stages_sync_run_id", "provider_sync_stages", ["sync_run_id"])
    op.create_index("ix_provider_sync_stages_status", "provider_sync_stages", ["status"])

    op.create_table(
        "provider_request_leases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("scope_key", sa.String(160), nullable=False),
        sa.Column("owner_token", sa.String(64), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "scope_key", name="uq_provider_request_lease"),
    )
    op.create_index("ix_provider_request_leases_expires_at", "provider_request_leases", ["expires_at"])


def downgrade() -> None:
    raise RuntimeError("Account/player enrichment migration is intentionally irreversible")

