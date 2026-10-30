"""Small persistence fixtures shared by migration and service tests."""

from pathlib import Path
import sqlite3


def create_legacy_database(path: Path) -> None:
    """Create the exact pre-Alembic schema with deterministic sample rows."""
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE teams (
                id INTEGER PRIMARY KEY,
                name VARCHAR(120) NOT NULL UNIQUE,
                logo_url VARCHAR(500),
                created_at DATETIME NOT NULL
            );
            CREATE TABLE players (
                id INTEGER PRIMARY KEY,
                team_id INTEGER NOT NULL REFERENCES teams(id),
                name VARCHAR(120) NOT NULL,
                jersey_number INTEGER NOT NULL,
                position VARCHAR(50) NOT NULL,
                preferred_foot VARCHAR(20)
            );
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY,
                home_team_id INTEGER NOT NULL REFERENCES teams(id),
                away_team_id INTEGER NOT NULL REFERENCES teams(id),
                match_date DATETIME NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                competition VARCHAR(120) NOT NULL
            );
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                match_id INTEGER NOT NULL REFERENCES matches(id),
                player_id INTEGER NOT NULL REFERENCES players(id),
                minute INTEGER NOT NULL,
                second INTEGER NOT NULL,
                type VARCHAR(20) NOT NULL,
                x_start FLOAT NOT NULL,
                y_start FLOAT NOT NULL,
                x_end FLOAT,
                y_end FLOAT,
                outcome VARCHAR(50),
                xg_value FLOAT
            );
            CREATE TABLE tracking_points (
                id INTEGER PRIMARY KEY,
                match_id INTEGER NOT NULL REFERENCES matches(id),
                player_id INTEGER NOT NULL REFERENCES players(id),
                timestamp_seconds FLOAT NOT NULL,
                x_coord FLOAT NOT NULL,
                y_coord FLOAT NOT NULL,
                speed_kmh FLOAT NOT NULL
            );

            INSERT INTO teams VALUES
                (11, 'StatX Legacy', NULL, '2025-01-01 00:00:00'),
                (12, 'Visitors', NULL, '2025-01-01 00:00:00');
            INSERT INTO players VALUES
                (21, 11, 'Amina Ben Salah', 8, 'midfielder', 'left');
            INSERT INTO matches VALUES
                (31, 11, 12, '2025-02-01 18:00:00', 2, 1, 'Legacy Cup');
            INSERT INTO events VALUES
                (41, 31, 21, 17, 4, 'pass', 45, 31, 68, 29, 'complete', NULL);
            INSERT INTO tracking_points VALUES
                (51, 31, 21, 1024.5, 48.2, 29.1, 21.3);
            """
        )
        connection.commit()
    finally:
        connection.close()

