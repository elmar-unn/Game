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
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text='Dashboard', style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.subtitle = ttk.Label(self, text='Project overview', style='Subtle.TLabel')
        self.subtitle.grid(row=1, column=0, sticky='w', pady=(0, 12))

        cards_frame = ttk.Frame(self)
        cards_frame.grid(row=2, column=0, columnspan=2, sticky='new')
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

        labels = [
            ('total_games', 'Total games'),
            ('completed', 'Completed'),
            ('backlog', 'Backlog'),
            ('avg_rating', 'Average rating'),
            ('total_hours', 'Played hours'),
            ('wishlist_count', 'Wishlist items'),
            ('most_played', 'Most played game'),
            ('completion_rate', 'Completion rate %'),
        ]
        for idx, (key, title) in enumerate(labels):
            card = ttk.LabelFrame(cards_frame, text=title, padding=16)
            card.grid(row=idx // 4, column=idx % 4, sticky='nsew', padx=8, pady=8)
            value = ttk.Label(card, text='-', font=('Segoe UI', 18, 'bold'))
            value.pack(anchor='w')
            self.cards[key] = value

        status_frame = ttk.LabelFrame(self, text='Status breakdown', padding=14)
        status_frame.grid(row=3, column=0, sticky='nsew', padx=(0, 8), pady=(12, 0))
        status_frame.columnconfigure(0, weight=1)
        self.status_tree = ttk.Treeview(status_frame, columns=('status', 'count'), show='headings', height=8)
        self.status_tree.heading('status', text='Status')
        self.status_tree.heading('count', text='Count')
        self.status_tree.column('status', width=180, anchor='w')
        self.status_tree.column('count', width=80, anchor='center')
        self.status_tree.grid(row=0, column=0, sticky='nsew')

        recent_frame = ttk.LabelFrame(self, text='Recent sessions', padding=14)
        recent_frame.grid(row=3, column=1, sticky='nsew', padx=(8, 0), pady=(12, 0))
        recent_frame.columnconfigure(0, weight=1)
        self.recent_tree = ttk.Treeview(recent_frame, columns=('date', 'game', 'minutes'), show='headings', height=8)
        self.recent_tree.heading('date', text='Date')
        self.recent_tree.heading('game', text='Game')
        self.recent_tree.heading('minutes', text='Minutes')
        self.recent_tree.column('date', width=100, anchor='center')
        self.recent_tree.column('game', width=220, anchor='w')
        self.recent_tree.column('minutes', width=90, anchor='center')
        self.recent_tree.grid(row=0, column=0, sticky='nsew')

    def refresh(self, selected_game_id: int | None = None):
        stats = self.db.get_dashboard_stats()
        for key, label in self.cards.items():
            label.config(text=str(stats.get(key, '-')))

        subtitle = 'Project overview'
        if selected_game_id is not None:
            details = self.db.get_game_details(selected_game_id)
            if details:
                subtitle = f"Focused on: {details['title']} • {round(details['total_minutes'] / 60, 1)} hours • {details['session_count']} sessions"
        self.subtitle.config(text=subtitle)

        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for row in self.db.get_status_breakdown():
            self.status_tree.insert('', 'end', values=(row['status'], row['count']))

        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        for row in self.db.get_recent_sessions():
            self.recent_tree.insert('', 'end', values=(row['session_date'], row['game_title'], row['duration_minutes']))
