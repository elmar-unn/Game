import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from database import DatabaseManager
from models import Game


class LibraryView(ttk.Frame):
    STATUS_VALUES = ['Backlog', 'Playing', 'Completed', 'Dropped']

    def __init__(self, parent: tk.Misc, db: DatabaseManager, on_data_changed=None, on_game_selected=None):
        super().__init__(parent, padding=14)
        self.db = db
        self.on_data_changed = on_data_changed or (lambda: None)
        self.on_game_selected = on_game_selected or (lambda _game_id: None)
        self.selected_game_id: int | None = None
        self.platform_options: dict[str, int] = {}
        self.genre_options: dict[str, int] = {}

        self.title_var = tk.StringVar()
        self.platform_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.rating_var = tk.StringVar(value='8')
        self.status_var = tk.StringVar(value='Backlog')
        self.completed_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value='All')
        self.platform_filter_var = tk.StringVar(value='All')
        self.genre_filter_var = tk.StringVar(value='All')
        self.stats_var = tk.StringVar(value='0 games loaded')

        self._build_ui()
        self.refresh_reference_data()
        self.load_games(trigger_refresh=False)

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        form = ttk.LabelFrame(self, text='Game Editor', padding=14)
        form.grid(row=0, column=0, sticky='ns')

        table_area = ttk.Frame(self)
        table_area.grid(row=0, column=1, sticky='nsew', padx=(16, 16))
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(2, weight=1)

        details = ttk.LabelFrame(self, text='Selected Game Details', padding=14)
        details.grid(row=0, column=2, sticky='nsew')
        details.columnconfigure(0, weight=1)

        ttk.Label(form, text='Library Manager', style='Header.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 12))
        ttk.Label(form, text='Title').grid(row=1, column=0, sticky='w')
        ttk.Entry(form, textvariable=self.title_var, width=30).grid(row=2, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Platform').grid(row=3, column=0, sticky='w')
        self.platform_combo = ttk.Combobox(form, textvariable=self.platform_var, state='readonly', width=27)
        self.platform_combo.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Genre').grid(row=5, column=0, sticky='w')
        self.genre_combo = ttk.Combobox(form, textvariable=self.genre_var, state='readonly', width=27)
        self.genre_combo.grid(row=6, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Rating (1-10)').grid(row=7, column=0, sticky='w')
        ttk.Spinbox(form, from_=1, to=10, textvariable=self.rating_var, width=10).grid(row=8, column=0, sticky='w', pady=(0, 8))
        ttk.Label(form, text='Status').grid(row=9, column=0, sticky='w')
        ttk.Combobox(form, textvariable=self.status_var, state='readonly', values=self.STATUS_VALUES).grid(row=10, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Checkbutton(form, text='Completed', variable=self.completed_var).grid(row=11, column=0, columnspan=2, sticky='w', pady=(0, 8))
        ttk.Label(form, text='Notes').grid(row=12, column=0, sticky='w')
        self.notes_text = tk.Text(form, width=28, height=8, wrap='word')
        self.notes_text.grid(row=13, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Button(form, text='Add Game', command=self.add_game).grid(row=14, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Update Selected', command=self.update_game).grid(row=14, column=1, sticky='ew', padx=(8, 0), pady=4)
        ttk.Button(form, text='Delete Selected', command=self.delete_game).grid(row=15, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Clear Form', command=self.clear_form).grid(row=15, column=1, sticky='ew', padx=(8, 0), pady=4)

        ttk.Label(table_area, text='Game Library', style='Header.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(table_area, textvariable=self.stats_var, style='Subtle.TLabel').grid(row=1, column=0, sticky='w', pady=(2, 8))

        filter_bar = ttk.Frame(table_area)
        filter_bar.grid(row=0, column=0, sticky='e')
        ttk.Entry(filter_bar, textvariable=self.search_var, width=18).grid(row=0, column=0, padx=4)
        ttk.Button(filter_bar, text='Search', command=self.load_games).grid(row=0, column=1, padx=4)
        ttk.Button(filter_bar, text='Reset', command=self.reset_filters).grid(row=0, column=2, padx=4)
        self.status_filter_combo = ttk.Combobox(filter_bar, textvariable=self.status_filter_var, state='readonly', width=11, values=['All'] + self.STATUS_VALUES)
        self.status_filter_combo.grid(row=0, column=3, padx=4)
        self.platform_filter_combo = ttk.Combobox(filter_bar, textvariable=self.platform_filter_var, state='readonly', width=12)
        self.platform_filter_combo.grid(row=0, column=4, padx=4)
        self.genre_filter_combo = ttk.Combobox(filter_bar, textvariable=self.genre_filter_var, state='readonly', width=12)
        self.genre_filter_combo.grid(row=0, column=5, padx=4)
        ttk.Button(filter_bar, text='Export CSV', command=self.export_csv).grid(row=0, column=6, padx=4)
        for combo in [self.status_filter_combo, self.platform_filter_combo, self.genre_filter_combo]:
            combo.bind('<<ComboboxSelected>>', lambda _e: self.load_games())

        columns = ('id', 'title', 'platform', 'genre', 'rating', 'status', 'completed', 'sessions', 'hours', 'date_added')
        self.tree = ttk.Treeview(table_area, columns=columns, show='headings', height=20)
        headings = ['ID', 'Title', 'Platform', 'Genre', 'Rating', 'Status', 'Completed', 'Sessions', 'Hours', 'Added']
        widths = [45, 220, 130, 110, 60, 95, 80, 75, 75, 125]
        for col, head, width in zip(columns, headings, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=width, anchor='center')
        self.tree.column('title', anchor='w')
        self.tree.grid(row=2, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        scrollbar = ttk.Scrollbar(table_area, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky='ns')

        self.details_value = tk.Text(details, height=26, wrap='word', state='disabled')
        self.details_value.grid(row=0, column=0, sticky='nsew')

    def refresh_reference_data(self):
        platforms = self.db.get_platforms()
        genres = self.db.get_genres()
        self.platform_options = {row['name']: row['id'] for row in platforms}
        self.genre_options = {row['name']: row['id'] for row in genres}
        platform_names = list(self.platform_options.keys())
        genre_names = list(self.genre_options.keys())
        self.platform_combo.configure(values=platform_names)
        self.genre_combo.configure(values=genre_names)
        self.platform_filter_combo.configure(values=['All'] + platform_names)
        self.genre_filter_combo.configure(values=['All'] + genre_names)
        if not self.platform_var.get() and platform_names:
            self.platform_var.set(platform_names[0])
        if not self.genre_var.get() and genre_names:
            self.genre_var.set(genre_names[0])
        if not self.platform_filter_var.get():
            self.platform_filter_var.set('All')
        if not self.genre_filter_var.get():
            self.genre_filter_var.set('All')

    def _build_game_from_form(self) -> Game | None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror('Validation error', 'Title is required.')
            return None
        try:
            rating = int(self.rating_var.get())
            if not 1 <= rating <= 10:
                raise ValueError
        except ValueError:
            messagebox.showerror('Validation error', 'Rating must be 1-10.')
            return None
        return Game(
            id=self.selected_game_id,
            title=title,
            platform_id=self.platform_options[self.platform_var.get()],
            genre_id=self.genre_options[self.genre_var.get()],
            rating=rating,
            status=self.status_var.get(),
            completed=1 if self.completed_var.get() else 0,
            notes=self.notes_text.get('1.0', 'end').strip(),
            date_added=self.db.now_string(),
        )

    def load_games(self, trigger_refresh: bool = True):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_games(
            search=self.search_var.get(),
            status_filter=self.status_filter_var.get(),
            platform_filter=self.platform_filter_var.get(),
            genre_filter=self.genre_filter_var.get(),
        )
        for row in rows:
            self.tree.insert('', 'end', values=(
                row['id'], row['title'], row['platform_name'], row['genre_name'], row['rating'], row['status'],
                'Yes' if row['completed'] else 'No', row['session_count'], round(row['total_minutes'] / 60, 1), row['date_added']
            ))
        total_hours = round(sum(row['total_minutes'] for row in rows) / 60, 1) if rows else 0
        self.stats_var.set(f'{len(rows)} games loaded • {total_hours} total hours in current view')
        if trigger_refresh:
            self.on_data_changed()

    def add_game(self):
        game = self._build_game_from_form()
        if game is None:
            return
        self.db.add_game(game)
        self.clear_form()
        self.load_games()

    def update_game(self):
        if self.selected_game_id is None:
            messagebox.showwarning('No selection', 'Select a game first.')
            return
        game = self._build_game_from_form()
        if game is None:
            return
        self.db.update_game(self.selected_game_id, game)
        self.clear_form()
        self.load_games()

    def delete_game(self):
        if self.selected_game_id is None:
            messagebox.showwarning('No selection', 'Select a game first.')
            return
        if not messagebox.askyesno('Confirm delete', 'Delete selected game and its sessions?'):
            return
        self.db.delete_game(self.selected_game_id)
        self.clear_form()
        self.load_games()

    def clear_form(self):
        self.selected_game_id = None
        self.title_var.set('')
        if self.platform_combo['values']:
            self.platform_var.set(self.platform_combo['values'][0])
        if self.genre_combo['values']:
            self.genre_var.set(self.genre_combo['values'][0])
        self.rating_var.set('8')
        self.status_var.set('Backlog')
        self.completed_var.set(False)
        self.notes_text.delete('1.0', 'end')
        self._set_details_text('Select a game from the table to see details.')
        self.on_game_selected(None)

    def reset_filters(self):
        self.search_var.set('')
        self.status_filter_var.set('All')
        self.platform_filter_var.set('All')
        self.genre_filter_var.set('All')
        self.load_games(trigger_refresh=False)

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(
            title='Export library to CSV',
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')],
            initialfile='gamevault_library.csv',
        )
        if not filepath:
            return
        self.db.export_library_csv(filepath)
        messagebox.showinfo('Export complete', f'Library exported to:\n{filepath}')

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], 'values')
        self.selected_game_id = int(values[0])
        details = self.db.get_game_details(self.selected_game_id)
        if not details:
            return
        self.title_var.set(details['title'])
        self.platform_var.set(details['platform_name'])
        self.genre_var.set(details['genre_name'])
        self.rating_var.set(str(details['rating']))
        self.status_var.set(details['status'])
        self.completed_var.set(bool(details['completed']))
        self.notes_text.delete('1.0', 'end')
        self.notes_text.insert('1.0', details['notes'])
        self._set_details_text(
            f"Title: {details['title']}\n"
            f"Platform: {details['platform_name']}\n"
            f"Genre: {details['genre_name']}\n"
            f"Rating: {details['rating']}/10\n"
            f"Status: {details['status']}\n"
            f"Completed: {'Yes' if details['completed'] else 'No'}\n"
            f"Sessions logged: {details['session_count']}\n"
            f"Hours played: {round(details['total_minutes'] / 60, 1)}\n"
            f"Last session: {details['last_session_date'] or '-'}\n"
            f"Added: {details['date_added']}\n\n"
            f"Notes:\n{details['notes'] or '-'}"
        )
        self.on_game_selected(self.selected_game_id)

    def _set_details_text(self, text: str) -> None:
        self.details_value.configure(state='normal')
        self.details_value.delete('1.0', 'end')
        self.details_value.insert('1.0', text)
        self.details_value.configure(state='disabled')
