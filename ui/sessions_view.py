import tkinter as tk
from tkinter import messagebox, ttk

from database import DatabaseManager
from models import PlaySession


class SessionsView(ttk.Frame):
    def __init__(self, parent: tk.Misc, db: DatabaseManager, on_data_changed=None):
        super().__init__(parent, padding=14)
        self.db = db
        self.on_data_changed = on_data_changed or (lambda: None)
        self.game_map: dict[str, int] = {}
        self.selected_session_id: int | None = None
        self.selected_game_id: int | None = None

        self.game_var = tk.StringVar()
        self.date_var = tk.StringVar(value=self.db.today_string())
        self.duration_var = tk.StringVar(value='60')
        self.filter_var = tk.StringVar(value='All games')

        self._build_ui()
        self.refresh_games()
        self.load_sessions(trigger_refresh=False)

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        form = ttk.LabelFrame(self, text='Log Session', padding=14)
        form.grid(row=0, column=0, sticky='ns')
        table = ttk.Frame(self)
        table.grid(row=0, column=1, sticky='nsew', padx=(16, 0))
        table.columnconfigure(0, weight=1)
        table.rowconfigure(2, weight=1)

        ttk.Label(form, text='Play Sessions', style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 12))
        ttk.Label(form, text='Game').grid(row=1, column=0, sticky='w')
        self.game_combo = ttk.Combobox(form, textvariable=self.game_var, state='readonly', width=30)
        self.game_combo.grid(row=2, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Session date (YYYY-MM-DD)').grid(row=3, column=0, sticky='w')
        ttk.Entry(form, textvariable=self.date_var, width=30).grid(row=4, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Duration (minutes)').grid(row=5, column=0, sticky='w')
        ttk.Spinbox(form, from_=5, to=999, increment=5, textvariable=self.duration_var, width=10).grid(row=6, column=0, sticky='w', pady=(0, 8))
        ttk.Label(form, text='Notes').grid(row=7, column=0, sticky='w')
        self.notes_text = tk.Text(form, width=30, height=7, wrap='word')
        self.notes_text.grid(row=8, column=0, sticky='ew', pady=(0, 8))
        ttk.Button(form, text='Add Session', command=self.add_session).grid(row=9, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Delete Selected', command=self.delete_session).grid(row=10, column=0, sticky='ew', pady=4)

        ttk.Label(table, text='Recent Sessions', style='Header.TLabel').grid(row=0, column=0, sticky='w')
        filter_bar = ttk.Frame(table)
        filter_bar.grid(row=0, column=0, sticky='e')
        self.filter_combo = ttk.Combobox(filter_bar, textvariable=self.filter_var, state='readonly', width=26)
        self.filter_combo.grid(row=0, column=0, padx=4)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda _e: self.on_filter_changed())
        ttk.Button(filter_bar, text='Show All', command=self.show_all).grid(row=0, column=1, padx=4)

        self.summary_label = ttk.Label(table, text='0 sessions loaded', style='Subtle.TLabel')
        self.summary_label.grid(row=1, column=0, sticky='w', pady=(2, 8))

        columns = ('id', 'game', 'date', 'duration', 'notes')
        self.tree = ttk.Treeview(table, columns=columns, show='headings', height=18)
        widths = [45, 220, 110, 90, 320]
        headers = ['ID', 'Game', 'Date', 'Minutes', 'Notes']
        for col, head, width in zip(columns, headers, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=width, anchor='center')
        self.tree.column('game', anchor='w')
        self.tree.column('notes', anchor='w')
        self.tree.grid(row=2, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        scrollbar = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky='ns')

    def refresh_games(self):
        rows = self.db.get_game_choices()
        self.game_map = {row['title']: row['id'] for row in rows}
        values = list(self.game_map.keys())
        self.game_combo.configure(values=values)
        self.filter_combo.configure(values=['All games'] + values)
        if values and not self.game_var.get():
            self.game_var.set(values[0])
        if not self.filter_var.get():
            self.filter_var.set('All games')

    def set_selected_game(self, game_id: int | None):
        self.selected_game_id = game_id
        if game_id is None:
            self.filter_var.set('All games')
            self.load_sessions(trigger_refresh=False)
            return
        for title, gid in self.game_map.items():
            if gid == game_id:
                self.game_var.set(title)
                self.filter_var.set(title)
                break
        self.load_sessions(trigger_refresh=False)

    def on_filter_changed(self):
        self.selected_game_id = self.game_map.get(self.filter_var.get())
        self.load_sessions(trigger_refresh=False)

    def show_all(self):
        self.selected_game_id = None
        self.filter_var.set('All games')
        self.load_sessions(trigger_refresh=False)

    def load_sessions(self, trigger_refresh: bool = True):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_play_sessions(self.selected_game_id)
        for row in rows:
            self.tree.insert('', 'end', values=(row['id'], row['game_title'], row['session_date'], row['duration_minutes'], row['notes']))
        total_minutes = sum(row['duration_minutes'] for row in rows)
        self.summary_label.config(text=f'{len(rows)} sessions loaded • {round(total_minutes / 60, 1)} hours total')
        if trigger_refresh:
            self.on_data_changed()

    def add_session(self):
        if not self.game_var.get():
            messagebox.showerror('No games', 'Add a game to the library first.')
            return
        try:
            duration = int(self.duration_var.get())
            if duration <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Validation error', 'Duration must be a positive number.')
            return
        session = PlaySession(None, self.game_map[self.game_var.get()], self.date_var.get().strip(), duration, self.notes_text.get('1.0', 'end').strip())
        self.db.add_play_session(session)
        self.notes_text.delete('1.0', 'end')
        self.duration_var.set('60')
        self.selected_game_id = self.game_map[self.game_var.get()]
        self.filter_var.set(self.game_var.get())
        self.load_sessions()

    def delete_session(self):
        if self.selected_session_id is None:
            messagebox.showwarning('No selection', 'Select a session first.')
            return
        if not messagebox.askyesno('Confirm delete', 'Delete selected session?'):
            return
        self.db.delete_play_session(self.selected_session_id)
        self.selected_session_id = None
        self.load_sessions()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], 'values')
        self.selected_session_id = int(values[0])
