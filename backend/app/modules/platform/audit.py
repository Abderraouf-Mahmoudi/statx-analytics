"""Append-only audit writer used by domain services."""

from sqlalchemy.orm import Session

from app.modules.platform.models import AuditLog


def write_audit(
    session: Session,
    *,
    actor_id: int | None,
    organization_id: int | None,
    action: str,
    entity_type: str,
    entity_public_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    """Stage an immutable audit record in the caller's transaction."""
    record = AuditLog(
        actor_id=actor_id,
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_public_id=entity_public_id,
        before=before,
        after=after,
    )
    session.add(record)
    session.flush()
    return record

