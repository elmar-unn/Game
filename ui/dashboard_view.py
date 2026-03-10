from tkinter import ttk

from database import DatabaseManager


class DashboardView(ttk.Frame):
    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, padding=14)
        self.db = db
        self.cards: dict[str, ttk.Label] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        for i in range(2):
            self.columnconfigure(i, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Label(self, text='Dashboard', style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.subtitle = ttk.Label(self, text='Project overview', style='Subtle.TLabel')
        self.subtitle.grid(row=1, column=0, sticky='w', pady=(0, 12))

        cards_frame = ttk.Frame(self)
        cards_frame.grid(row=2, column=0, columnspan=2, sticky='nsew')
        for i in range(5):
            cards_frame.columnconfigure(i, weight=1)

        labels = [
            ('total_games', 'Total games'),
            ('completed', 'Completed'),
            ('backlog', 'Backlog'),
            ('favorites', 'Favorites'),
            ('avg_rating', 'Average rating'),
            ('total_hours', 'Played hours'),
            ('wishlist_count', 'Wishlist items'),
            ('most_played', 'Most played'),
            ('newest_game', 'Newest added'),
            ('completion_rate', 'Completion rate %'),
        ]
        for idx, (key, title) in enumerate(labels):
            card = ttk.Frame(cards_frame, style='Card.TFrame', padding=14)
            card.grid(row=idx // 5, column=idx % 5, sticky='nsew', padx=6, pady=6)
            ttk.Label(card, text=title, style='StatTitle.TLabel').pack(anchor='w')
            value = ttk.Label(card, text='-', style='StatValue.TLabel')
            value.pack(anchor='w', pady=(6, 0))
            self.cards[key] = value

        status_frame = ttk.LabelFrame(self, text='Status breakdown', padding=12)
        status_frame.grid(row=3, column=0, sticky='nsew', padx=(0, 8), pady=(12, 0))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        self.status_tree = ttk.Treeview(status_frame, columns=('status', 'count'), show='headings', height=10)
        self.status_tree.heading('status', text='Status')
        self.status_tree.heading('count', text='Count')
        self.status_tree.column('status', width=220, anchor='w')
        self.status_tree.column('count', width=90, anchor='center')
        self.status_tree.grid(row=0, column=0, sticky='nsew')

        right = ttk.Frame(self)
        right.grid(row=3, column=1, sticky='nsew', padx=(8, 0), pady=(12, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        recent_frame = ttk.LabelFrame(right, text='Recent sessions', padding=12)
        recent_frame.grid(row=0, column=0, sticky='nsew')
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(0, weight=1)
        self.recent_tree = ttk.Treeview(recent_frame, columns=('date', 'game', 'minutes'), show='headings', height=7)
        self.recent_tree.heading('date', text='Date')
        self.recent_tree.heading('game', text='Game')
        self.recent_tree.heading('minutes', text='Minutes')
        self.recent_tree.column('date', width=100, anchor='center')
        self.recent_tree.column('game', width=220, anchor='w')
        self.recent_tree.column('minutes', width=90, anchor='center')
        self.recent_tree.grid(row=0, column=0, sticky='nsew')

        platform_frame = ttk.LabelFrame(right, text='Platform breakdown', padding=12)
        platform_frame.grid(row=1, column=0, sticky='nsew', pady=(12, 0))
        platform_frame.columnconfigure(0, weight=1)
        platform_frame.rowconfigure(0, weight=1)
        self.platform_tree = ttk.Treeview(platform_frame, columns=('platform', 'count'), show='headings', height=7)
        self.platform_tree.heading('platform', text='Platform')
        self.platform_tree.heading('count', text='Count')
        self.platform_tree.column('platform', width=240, anchor='w')
        self.platform_tree.column('count', width=90, anchor='center')
        self.platform_tree.grid(row=0, column=0, sticky='nsew')

    def refresh(self, selected_game_id: int | None = None):
        stats = self.db.get_dashboard_stats()
        for key, label in self.cards.items():
            label.config(text=str(stats.get(key, '-')))

        subtitle = 'Project overview'
        if selected_game_id is not None:
            details = self.db.get_game_details(selected_game_id)
            if details:
                subtitle = (
                    f"Focused on: {details['title']} • {round(details['total_minutes'] / 60, 1)} hours • "
                    f"{details['session_count']} sessions"
                )
        self.subtitle.config(text=subtitle)

        for tree in (self.status_tree, self.recent_tree, self.platform_tree):
            for item in tree.get_children():
                tree.delete(item)

        for row in self.db.get_status_breakdown():
            self.status_tree.insert('', 'end', values=(row['status'], row['count']))
        for row in self.db.get_recent_sessions():
            self.recent_tree.insert('', 'end', values=(row['session_date'], row['game_title'], row['duration_minutes']))
        for row in self.db.get_platform_breakdown():
            self.platform_tree.insert('', 'end', values=(row['platform_name'], row['count']))

    def apply_theme(self, _palette: dict[str, str]):
        pass
