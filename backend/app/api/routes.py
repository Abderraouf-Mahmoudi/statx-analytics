"""REST endpoints for teams, players, matches, events, and analytics."""

from pathlib import Path
from collections import Counter
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
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
from app.core.pdf_generator import (
    MatchReportData,
    MatchReportGenerator,
    ReportTeamMetrics,
    ReportVisuals,
)
from app.db.database import get_db
from app.db.models import Event, Match, Player, Team


router = APIRouter(prefix="/api")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPORT_ROOT = PROJECT_ROOT / "data" / "exports"
logger = logging.getLogger(__name__)


def _commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc


@router.get("/teams", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)) -> list[Team]:
    """Return all teams ordered alphabetically."""
    return list(db.scalars(select(Team).order_by(Team.name)).all())


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


@router.get("/matches", response_model=list[MatchRead])
def list_matches(db: Session = Depends(get_db)) -> list[Match]:
    """Return all matches, newest first."""
    return list(db.scalars(select(Match).order_by(Match.match_date.desc())).all())


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

    home_metrics = metrics(match.home_team, match.home_score)
    away_metrics = metrics(match.away_team, match.away_score)
    player_event_counts = Counter(event.player_id for event in events)
    key_player_id = player_event_counts.most_common(1)[0][0] if player_event_counts else None
    key_player = next(
        (event.player for event in events if event.player_id == key_player_id),
        None,
    )
    key_player_name = key_player.name if key_player else None

    return AnalyticsResponse(
        match_id=match.id,
        home=home_metrics,
        away=away_metrics,
        graphics={
            "shot_map": public_path(shot_path),
            "pass_map": public_path(pass_path),
            "heatmap": public_path(heatmap_path),
        },
        tactical_insights=_build_tactical_insights(
            events,
            home_metrics,
            away_metrics,
            key_player_name or "Aucun joueur",
            player_event_counts.get(key_player_id, 0),
        ),
        key_player=key_player_name,
    )


@router.get("/matches/{match_id}/pdf", response_class=FileResponse)
def download_match_report(
    match_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Generate and download the printable one-page report for a match."""
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
    analytics = get_match_analytics(match_id, None, db)
    player_event_counts = Counter(event.player_id for event in events)
    key_player_id = player_event_counts.most_common(1)[0][0] if player_event_counts else None
    key_player = next(
        (event.player for event in events if event.player_id == key_player_id),
        None,
    )
    key_player_name = key_player.name if key_player else "Aucun joueur"

    match_dir = EXPORT_ROOT / "matches" / str(match_id)
    shot_map = match_dir / "shot_map.png"
    pass_map = match_dir / f"pass_map_team_{match.home_team_id}.png"
    heatmap = match_dir / (
        f"heatmap_player_{key_player_id}.png" if key_player_id else "heatmap_match.png"
    )
    home_events = [
        event for event in events if event.player.team_id == match.home_team_id
    ]

    try:
        generate_shot_map(events, shot_map)
        generate_pass_map(home_events, None, pass_map)
        generate_heatmap(events, key_player_id, heatmap)

        insights = _build_tactical_insights(
            events,
            analytics.home,
            analytics.away,
            key_player_name,
            player_event_counts.get(key_player_id, 0),
        )
        report_data = MatchReportData(
            match_id=match.id,
            match_date=match.match_date,
            competition=match.competition,
            home=ReportTeamMetrics(
                name=analytics.home.team_name,
                score=analytics.home.score,
                total_xg=analytics.home.total_xg,
                possession=analytics.home.possession,
                shots_on_target=analytics.home.shots_on_target,
            ),
            away=ReportTeamMetrics(
                name=analytics.away.team_name,
                score=analytics.away.score,
                total_xg=analytics.away.total_xg,
                possession=analytics.away.possession,
                shots_on_target=analytics.away.shots_on_target,
            ),
            key_player_name=key_player_name,
            tactical_insights=insights,
        )
        report_path = MatchReportGenerator(EXPORT_ROOT).generate(
            report_data,
            ReportVisuals(
                shot_map=shot_map,
                pass_map=pass_map,
                heatmap=heatmap,
            ),
        )
    except Exception as exc:
        logger.exception("Unable to generate PDF report for match %s", match_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report or its analytics visuals",
        ) from exc

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=report_path.name,
    )


def _build_tactical_insights(
    events: list[Event],
    home: TeamMetrics,
    away: TeamMetrics,
    key_player_name: str,
    key_player_actions: int,
) -> list[str]:
    """Create three concise, data-backed observations for the PDF footer."""
    shots = [event for event in events if event.type == "shot"]
    shots_in_box = [
        event
        for event in shots
        if event.x_start >= 102 and 18 <= event.y_start <= 62
    ]
    box_share = round(len(shots_in_box) / len(shots) * 100) if shots else 0

    shot_insight = (
        f"{box_share}% des tirs ont été déclenchés depuis la surface de réparation."
        if shots
        else "Aucun tir n'a été enregistré pour cette rencontre."
    )
    if abs(home.total_xg - away.total_xg) < 0.01:
        xg_insight = f"Équilibre en xG : {home.total_xg:.2f} pour chaque équipe."
    else:
        xg_leader = home if home.total_xg > away.total_xg else away
        xg_trailer = away if xg_leader is home else home
        xg_insight = (
            f"{xg_leader.team_name} domine en xG avec "
            f"{xg_leader.total_xg:.2f} contre {xg_trailer.total_xg:.2f}."
        )

    if abs(home.possession - away.possession) < 0.1:
        possession_text = "La possession estimée est parfaitement équilibrée"
    else:
        possession_leader = home if home.possession > away.possession else away
        possession_text = (
            f"{possession_leader.team_name} contrôle "
            f"{possession_leader.possession:.1f}% de la possession estimée"
        )
    key_player_text = (
        f"{key_player_name} concentre {key_player_actions} actions"
        if key_player_actions
        else "aucun joueur clé ne se dégage"
    )

    return [
        shot_insight,
        xg_insight,
        f"{possession_text}; {key_player_text}.",
    ]

