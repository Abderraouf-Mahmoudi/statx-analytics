"""REST endpoints for teams, players, matches, events, and analytics."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.schemas import (
    AnalyticsResponse,
    EventCreate,
    EventRead,
    MatchCreate,
    MatchRead,
    PlayerCreate,
    PlayerRead,
    TeamCreate,
    TeamMetrics,
    TeamRead,
)
from app.core.analytics import generate_heatmap, generate_pass_map, generate_shot_map
from app.db.database import get_db
from app.db.models import Event, Match, Player, Team


router = APIRouter(prefix="/api")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPORT_ROOT = PROJECT_ROOT / "data" / "exports"


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc


@router.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)) -> Team:
    team = Team(name=payload.name, logo_url=str(payload.logo_url) if payload.logo_url else None)
    db.add(team)
    _commit_or_conflict(db, "A team with this name already exists")
    db.refresh(team)
    return team


@router.post("/players", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, db: Session = Depends(get_db)) -> Player:
    if db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    player = Player(**payload.model_dump())
    db.add(player)
    _commit_or_conflict(db, "Unable to create player")
    db.refresh(player)
    return player


@router.post("/matches", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db)) -> Match:
    team_ids = {payload.home_team_id, payload.away_team_id}
    existing_ids = set(db.scalars(select(Team.id).where(Team.id.in_(team_ids))))
    if existing_ids != team_ids:
        raise HTTPException(status_code=404, detail="Home or away team not found")
    match = Match(**payload.model_dump())
    db.add(match)
    _commit_or_conflict(db, "Unable to create match")
    db.refresh(match)
    return match


@router.post(
    "/matches/{match_id}/events",
    response_model=list[EventRead],
    status_code=status.HTTP_201_CREATED,
)
def create_events(
    match_id: int,
    payload: list[EventCreate],
    db: Session = Depends(get_db),
) -> list[Event]:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if not payload:
        raise HTTPException(status_code=422, detail="At least one event is required")

    player_ids = {event.player_id for event in payload}
    players = db.scalars(select(Player).where(Player.id.in_(player_ids))).all()
    players_by_id = {player.id: player for player in players}
    if set(players_by_id) != player_ids:
        raise HTTPException(status_code=404, detail="One or more players were not found")

    match_team_ids = {match.home_team_id, match.away_team_id}
    if any(player.team_id not in match_team_ids for player in players):
        raise HTTPException(status_code=422, detail="Every player must belong to a team in this match")

    records = [Event(match_id=match_id, **event.model_dump()) for event in payload]
    db.add_all(records)
    _commit_or_conflict(db, "Unable to create match events")
    for record in records:
        db.refresh(record)
    return records


@router.get("/matches/{match_id}/analytics", response_model=AnalyticsResponse)
def get_match_analytics(
    match_id: int,
    player_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> AnalyticsResponse:
    match = db.scalar(
        select(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .where(Match.id == match_id)
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    events = db.scalars(
        select(Event).options(joinedload(Event.player)).where(Event.match_id == match_id)
    ).all()
    if player_id is not None:
        selected = next((event.player for event in events if event.player_id == player_id), None)
        if selected is None:
            raise HTTPException(status_code=404, detail="Player has no events in this match")

    team_ids = (match.home_team_id, match.away_team_id)
    by_team = {
        team_id: [event for event in events if event.player.team_id == team_id]
        for team_id in team_ids
    }
    pass_counts = {
        team_id: sum(event.type == "pass" for event in team_events)
        for team_id, team_events in by_team.items()
    }
    total_passes = sum(pass_counts.values())

    def metrics(team: Team, score: int) -> TeamMetrics:
        team_events = by_team[team.id]
        shots = [event for event in team_events if event.type == "shot"]
        possession = (
            round(pass_counts[team.id] / total_passes * 100, 1)
            if total_passes
            else 50.0
        )
        return TeamMetrics(
            team_id=team.id,
            team_name=team.name,
            score=score,
            total_xg=round(sum(event.xg_value or 0 for event in shots), 2),
            shots_on_target=sum(
                str(event.outcome).lower() in {"goal", "on_target", "saved"}
                for event in shots
            ),
            possession=possession,
        )

    output_dir = EXPORT_ROOT / "matches" / str(match_id)
    suffix = f"_player_{player_id}" if player_id else ""
    shot_path = generate_shot_map(events, output_dir / "shot_map.png")
    pass_path = generate_pass_map(events, player_id, output_dir / f"pass_map{suffix}.png")
    heatmap_path = generate_heatmap(events, player_id, output_dir / f"heatmap{suffix}.png")

    def public_path(path: Path) -> str:
        return f"/exports/{path.relative_to(EXPORT_ROOT).as_posix()}"

    return AnalyticsResponse(
        match_id=match.id,
        home=metrics(match.home_team, match.home_score),
        away=metrics(match.away_team, match.away_score),
        graphics={
            "shot_map": public_path(shot_path),
            "pass_map": public_path(pass_path),
            "heatmap": public_path(heatmap_path),
        },
    )

