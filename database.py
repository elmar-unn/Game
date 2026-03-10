import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from models import Game, PlaySession, WishlistItem

DEFAULT_DB_PATH = Path(__file__).with_name('gamevault.db')


class DatabaseManager:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')

    def now_string(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M')

    def today_string(self) -> str:
        return datetime.now().strftime('%Y-%m-%d')

    def initialize(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            '''
            CREATE TABLE IF NOT EXISTS platforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 10),
                status TEXT NOT NULL DEFAULT 'Backlog',
                completed INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                date_added TEXT NOT NULL,
                FOREIGN KEY (platform_id) REFERENCES platforms(id),
                FOREIGN KEY (genre_id) REFERENCES genres(id)
            );

            CREATE TABLE IF NOT EXISTS play_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform_id INTEGER NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium',
                added_at TEXT NOT NULL,
                FOREIGN KEY (platform_id) REFERENCES platforms(id)
            );
            '''
        )
        self.conn.commit()
        self._migrate_stage1_if_needed()

    def _table_columns(self, table_name: str) -> set[str]:
        rows = self.conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        return {row['name'] for row in rows}

    def _migrate_stage1_if_needed(self) -> None:
        cols = self._table_columns('games')
        if 'platform' not in cols:
            return

        legacy_rows = self.conn.execute('SELECT * FROM games').fetchall()
        self.conn.execute('ALTER TABLE games RENAME TO games_stage1_backup')
        self.conn.executescript(
            '''
            CREATE TABLE games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 10),
                status TEXT NOT NULL DEFAULT 'Backlog',
                completed INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                date_added TEXT NOT NULL,
                FOREIGN KEY (platform_id) REFERENCES platforms(id),
                FOREIGN KEY (genre_id) REFERENCES genres(id)
            );
            '''
        )
        for row in legacy_rows:
            platform_id = self.ensure_platform(row['platform'])
            genre_id = self.ensure_genre(row['genre'] or 'Other')
            self.conn.execute(
                '''
                INSERT INTO games (title, platform_id, genre_id, rating, status, completed, notes, date_added)
                VALUES (?, ?, ?, ?, ?, ?, '', ?)
                ''',
                (
                    row['title'],
                    platform_id,
                    genre_id,
                    row['rating'] or 1,
                    row['status'] or 'Backlog',
                    row['completed'] or 0,
                    row['date_added'] or self.now_string(),
                ),
            )
        self.conn.execute('DROP TABLE games_stage1_backup')
        self.conn.commit()

    def seed_if_empty(self) -> None:
        for platform in ['PC', 'PlayStation 5', 'Nintendo Switch', 'Xbox Series X/S', 'Mobile']:
            self.ensure_platform(platform)
        for genre in ['RPG', 'Roguelike', 'Sandbox', 'Action', 'Adventure', 'Strategy', 'Other']:
            self.ensure_genre(genre)

        if self.conn.execute('SELECT COUNT(*) FROM games').fetchone()[0] == 0:
            samples = [
                Game(None, 'Elden Ring', self.ensure_platform('PC'), self.ensure_genre('RPG'), 10, 'Completed', 1,
                     'Massive open world and great bosses.', self.now_string()),
                Game(None, 'Hades', self.ensure_platform('Nintendo Switch'), self.ensure_genre('Roguelike'), 9, 'Playing', 0,
                     'Great for short sessions.', self.now_string()),
                Game(None, 'Minecraft', self.ensure_platform('PC'), self.ensure_genre('Sandbox'), 9, 'Backlog', 0,
                     'Need to start a new survival world.', self.now_string()),
            ]
            for game in samples:
                self.add_game(game)

        if self.conn.execute('SELECT COUNT(*) FROM play_sessions').fetchone()[0] == 0:
            first_game_id = self.conn.execute('SELECT id FROM games ORDER BY id LIMIT 1').fetchone()
            if first_game_id:
                self.add_play_session(PlaySession(None, first_game_id['id'], self.today_string(), 90, 'Explored a new area.'))

        if self.conn.execute('SELECT COUNT(*) FROM wishlist').fetchone()[0] == 0:
            self.add_wishlist_item(WishlistItem(None, 'Hollow Knight: Silksong', self.ensure_platform('PC'), 'High', self.now_string()))

    def ensure_platform(self, name: str) -> int:
        name = (name or 'Unknown').strip()
        cur = self.conn.cursor()
        cur.execute('INSERT OR IGNORE INTO platforms (name) VALUES (?)', (name,))
        self.conn.commit()
        row = cur.execute('SELECT id FROM platforms WHERE name = ?', (name,)).fetchone()
        return int(row['id'])

    def ensure_genre(self, name: str) -> int:
        name = (name or 'Other').strip()
        cur = self.conn.cursor()
        cur.execute('INSERT OR IGNORE INTO genres (name) VALUES (?)', (name,))
        self.conn.commit()
        row = cur.execute('SELECT id FROM genres WHERE name = ?', (name,)).fetchone()
        return int(row['id'])

    def get_platforms(self) -> list[sqlite3.Row]:
        return self.conn.execute('SELECT id, name FROM platforms ORDER BY name').fetchall()

    def get_genres(self) -> list[sqlite3.Row]:
        return self.conn.execute('SELECT id, name FROM genres ORDER BY name').fetchall()

    def add_game(self, game: Game) -> None:
        self.conn.execute(
            '''
            INSERT INTO games (title, platform_id, genre_id, rating, status, completed, notes, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (game.title, game.platform_id, game.genre_id, game.rating, game.status, game.completed, game.notes, game.date_added),
        )
        self.conn.commit()

    def update_game(self, game_id: int, game: Game) -> None:
        self.conn.execute(
            '''
            UPDATE games
            SET title = ?, platform_id = ?, genre_id = ?, rating = ?, status = ?, completed = ?, notes = ?
            WHERE id = ?
            ''',
            (game.title, game.platform_id, game.genre_id, game.rating, game.status, game.completed, game.notes, game_id),
        )
        self.conn.commit()

    def delete_game(self, game_id: int) -> None:
        self.conn.execute('DELETE FROM games WHERE id = ?', (game_id,))
        self.conn.commit()

    def fetch_games(self, search: str = '', status_filter: str = 'All', platform_filter: str = 'All', genre_filter: str = 'All') -> list[sqlite3.Row]:
        query = '''
            SELECT g.*, p.name AS platform_name, ge.name AS genre_name,
                   COALESCE(SUM(ps.duration_minutes), 0) AS total_minutes,
                   COUNT(ps.id) AS session_count
            FROM games g
            JOIN platforms p ON p.id = g.platform_id
            JOIN genres ge ON ge.id = g.genre_id
            LEFT JOIN play_sessions ps ON ps.game_id = g.id
            WHERE 1=1
        '''
        params: list[str] = []
        search = search.strip()
        if search:
            wildcard = f'%{search}%'
            query += ' AND (g.title LIKE ? OR p.name LIKE ? OR ge.name LIKE ? OR g.status LIKE ? OR g.notes LIKE ?)'
            params.extend([wildcard] * 5)
        if status_filter != 'All':
            query += ' AND g.status = ?'
            params.append(status_filter)
        if platform_filter != 'All':
            query += ' AND p.name = ?'
            params.append(platform_filter)
        if genre_filter != 'All':
            query += ' AND ge.name = ?'
            params.append(genre_filter)
        query += ' GROUP BY g.id ORDER BY g.date_added DESC, g.id DESC'
        return self.conn.execute(query, params).fetchall()

    def get_game_choices(self) -> list[sqlite3.Row]:
        return self.conn.execute('SELECT id, title FROM games ORDER BY title').fetchall()

    def get_game_details(self, game_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            '''
            SELECT g.*, p.name AS platform_name, ge.name AS genre_name,
                   COALESCE(SUM(ps.duration_minutes), 0) AS total_minutes,
                   COUNT(ps.id) AS session_count,
                   MAX(ps.session_date) AS last_session_date
            FROM games g
            JOIN platforms p ON p.id = g.platform_id
            JOIN genres ge ON ge.id = g.genre_id
            LEFT JOIN play_sessions ps ON ps.game_id = g.id
            WHERE g.id = ?
            GROUP BY g.id
            ''',
            (game_id,),
        ).fetchone()

    def add_play_session(self, session: PlaySession) -> None:
        self.conn.execute(
            '''
            INSERT INTO play_sessions (game_id, session_date, duration_minutes, notes)
            VALUES (?, ?, ?, ?)
            ''',
            (session.game_id, session.session_date, session.duration_minutes, session.notes),
        )
        self.conn.commit()

    def fetch_play_sessions(self, game_id: int | None = None) -> list[sqlite3.Row]:
        query = '''
            SELECT ps.id, ps.game_id, g.title AS game_title, ps.session_date, ps.duration_minutes, ps.notes
            FROM play_sessions ps
            JOIN games g ON g.id = ps.game_id
        '''
        params: list[int] = []
        if game_id is not None:
            query += ' WHERE ps.game_id = ?'
            params.append(game_id)
        query += ' ORDER BY ps.session_date DESC, ps.id DESC'
        return self.conn.execute(query, params).fetchall()

    def delete_play_session(self, session_id: int) -> None:
        self.conn.execute('DELETE FROM play_sessions WHERE id = ?', (session_id,))
        self.conn.commit()

    def add_wishlist_item(self, item: WishlistItem) -> None:
        self.conn.execute(
            '''
            INSERT INTO wishlist (title, platform_id, priority, added_at)
            VALUES (?, ?, ?, ?)
            ''',
            (item.title, item.platform_id, item.priority, item.added_at),
        )
        self.conn.commit()

    def fetch_wishlist(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            '''
            SELECT w.id, w.title, p.name AS platform_name, w.priority, w.added_at
            FROM wishlist w
            JOIN platforms p ON p.id = w.platform_id
            ORDER BY CASE w.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, w.id DESC
            '''
        ).fetchall()

    def delete_wishlist_item(self, item_id: int) -> None:
        self.conn.execute('DELETE FROM wishlist WHERE id = ?', (item_id,))
        self.conn.commit()

    def get_recent_sessions(self, limit: int = 8) -> list[sqlite3.Row]:
        return self.conn.execute(
            '''
            SELECT ps.session_date, g.title AS game_title, ps.duration_minutes
            FROM play_sessions ps
            JOIN games g ON g.id = ps.game_id
            ORDER BY ps.session_date DESC, ps.id DESC
            LIMIT ?
            ''',
            (limit,),
        ).fetchall()

    def get_status_breakdown(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            '''
            SELECT status, COUNT(*) AS count
            FROM games
            GROUP BY status
            ORDER BY count DESC, status
            '''
        ).fetchall()

    def get_dashboard_stats(self) -> dict[str, str | int | float]:
        cur = self.conn.cursor()
        total_games = cur.execute('SELECT COUNT(*) FROM games').fetchone()[0]
        completed = cur.execute('SELECT COUNT(*) FROM games WHERE completed = 1').fetchone()[0]
        backlog = cur.execute("SELECT COUNT(*) FROM games WHERE status = 'Backlog'").fetchone()[0]
        avg_rating = cur.execute('SELECT ROUND(AVG(rating), 1) FROM games').fetchone()[0] or '-'
        total_minutes = cur.execute('SELECT COALESCE(SUM(duration_minutes), 0) FROM play_sessions').fetchone()[0]
        wishlist_count = cur.execute('SELECT COUNT(*) FROM wishlist').fetchone()[0]
        most_played = cur.execute(
            '''
            SELECT g.title, SUM(ps.duration_minutes) AS total_minutes
            FROM play_sessions ps
            JOIN games g ON g.id = ps.game_id
            GROUP BY g.id
            ORDER BY total_minutes DESC
            LIMIT 1
            '''
        ).fetchone()
        completion_rate = round((completed / total_games) * 100, 1) if total_games else 0
        return {
            'total_games': total_games,
            'completed': completed,
            'backlog': backlog,
            'avg_rating': avg_rating,
            'total_hours': round(total_minutes / 60, 1),
            'wishlist_count': wishlist_count,
            'most_played': most_played['title'] if most_played else '-',
            'completion_rate': completion_rate,
        }

    def export_library_csv(self, filepath: str | Path) -> None:
        rows = self.fetch_games()
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Title', 'Platform', 'Genre', 'Rating', 'Status', 'Completed', 'Sessions', 'Hours Played', 'Added', 'Notes'])
            for row in rows:
                writer.writerow([
                    row['id'], row['title'], row['platform_name'], row['genre_name'], row['rating'], row['status'],
                    'Yes' if row['completed'] else 'No', row['session_count'], round(row['total_minutes'] / 60, 1), row['date_added'], row['notes'],
                ])

    def close(self) -> None:
        self.conn.close()
