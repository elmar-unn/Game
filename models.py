from dataclasses import dataclass


@dataclass
class Game:
    id: int | None
    title: str
    platform_id: int
    genre_id: int
    rating: int
    status: str
    completed: int
    notes: str
    date_added: str
    release_year: int | None = None
    publisher: str = ''
    cover_path: str = ''
    favorite: int = 0


@dataclass
class PlaySession:
    id: int | None
    game_id: int
    session_date: str
    duration_minutes: int
    notes: str


@dataclass
class WishlistItem:
    id: int | None
    title: str
    platform_id: int
    priority: str
    added_at: str
