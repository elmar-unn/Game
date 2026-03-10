import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from database import DatabaseManager
from models import Game


class LibraryView(ttk.Frame):
    STATUS_VALUES = ['Backlog', 'Playing', 'Completed', 'Dropped']
    SORT_VALUES = ['Newest first', 'Title A-Z', 'Rating high-low', 'Hours played', 'Release year']
    IMAGE_FILETYPES = [('Image files', '*.png *.jpg *.jpeg *.webp *.gif *.bmp'), ('All files', '*.*')]

    def __init__(self, parent: tk.Misc, db: DatabaseManager, on_data_changed=None, on_game_selected=None):
        super().__init__(parent, padding=14)
        self.db = db
        self.on_data_changed = on_data_changed or (lambda: None)
        self.on_game_selected = on_game_selected or (lambda _game_id: None)
        self.selected_game_id: int | None = None
        self.platform_options: dict[str, int] = {}
        self.genre_options: dict[str, int] = {}
        self.cover_preview: ImageTk.PhotoImage | None = None
        self.current_palette: dict[str, str] = {}

        self.project_root = Path(__file__).resolve().parents[1]
        self.covers_dir = self.project_root / 'covers'
        self.covers_dir.mkdir(exist_ok=True)

        self.title_var = tk.StringVar()
        self.platform_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.rating_var = tk.StringVar(value='8')
        self.status_var = tk.StringVar(value='Backlog')
        self.completed_var = tk.BooleanVar(value=False)
        self.favorite_var = tk.BooleanVar(value=False)
        self.release_year_var = tk.StringVar()
        self.publisher_var = tk.StringVar()
        self.cover_path_var = tk.StringVar()
        self.cover_hint_var = tk.StringVar(value='Use “Import Cover” to copy an image into the project automatically.')
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value='All')
        self.platform_filter_var = tk.StringVar(value='All')
        self.genre_filter_var = tk.StringVar(value='All')
        self.favorite_filter_var = tk.BooleanVar(value=False)
        self.sort_var = tk.StringVar(value='Newest first')
        self.stats_var = tk.StringVar(value='0 games loaded')
        self.details_var = tk.StringVar(value='Select a game to see details.')

        self._build_ui()
        self.refresh_reference_data()
        self.load_games(trigger_refresh=False)

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        form = ttk.LabelFrame(self, text='Game Editor', padding=14)
        form.grid(row=0, column=0, sticky='ns')
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        table_area = ttk.Frame(self)
        table_area.grid(row=0, column=1, sticky='nsew', padx=(16, 16))
        table_area.columnconfigure(0, weight=1)
        table_area.rowconfigure(2, weight=1)

        details = ttk.LabelFrame(self, text='Selected Game Details', padding=14)
        details.grid(row=0, column=2, sticky='nsew')
        details.columnconfigure(0, weight=1)
        details.rowconfigure(3, weight=1)

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
        ttk.Label(form, text='Release year').grid(row=11, column=0, sticky='w')
        ttk.Entry(form, textvariable=self.release_year_var, width=14).grid(row=12, column=0, sticky='w', pady=(0, 8))
        ttk.Label(form, text='Publisher').grid(row=11, column=1, sticky='w')
        ttk.Entry(form, textvariable=self.publisher_var, width=14).grid(row=12, column=1, sticky='ew', pady=(0, 8), padx=(8, 0))
        ttk.Checkbutton(form, text='Completed', variable=self.completed_var).grid(row=13, column=0, sticky='w')
        ttk.Checkbutton(form, text='Favorite', variable=self.favorite_var).grid(row=13, column=1, sticky='w')
        ttk.Label(form, text='Cover image').grid(row=14, column=0, sticky='w', pady=(6, 0))
        ttk.Entry(form, textvariable=self.cover_path_var, width=24).grid(row=15, column=0, columnspan=2, sticky='ew')
        ttk.Button(form, text='Import Cover', command=self.browse_cover, style='Accent.TButton').grid(row=16, column=0, sticky='ew', pady=(8, 4))
        ttk.Button(form, text='Clear Cover', command=self.clear_cover).grid(row=16, column=1, sticky='ew', pady=(8, 4), padx=(8, 0))
        ttk.Label(form, textvariable=self.cover_hint_var, style='Subtle.TLabel', wraplength=260, justify='left').grid(row=17, column=0, columnspan=2, sticky='w', pady=(0, 8))
        ttk.Label(form, text='Notes').grid(row=18, column=0, sticky='w')
        self.notes_text = tk.Text(form, width=28, height=6, wrap='word', relief='flat', borderwidth=0)
        self.notes_text.grid(row=19, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        ttk.Button(form, text='Add Game', command=self.add_game, style='Accent.TButton').grid(row=20, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Update Selected', command=self.update_game).grid(row=20, column=1, sticky='ew', padx=(8, 0), pady=4)
        ttk.Button(form, text='Delete Selected', command=self.delete_game).grid(row=21, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Clear Form', command=self.clear_form).grid(row=21, column=1, sticky='ew', padx=(8, 0), pady=4)

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
        self.sort_combo = ttk.Combobox(filter_bar, textvariable=self.sort_var, state='readonly', width=15, values=self.SORT_VALUES)
        self.sort_combo.grid(row=0, column=6, padx=4)
        ttk.Checkbutton(filter_bar, text='Favorites only', variable=self.favorite_filter_var, command=self.load_games).grid(row=0, column=7, padx=4)
        ttk.Button(filter_bar, text='Export CSV', command=self.export_csv).grid(row=0, column=8, padx=4)
        ttk.Button(filter_bar, text='Export JSON', command=self.export_json).grid(row=0, column=9, padx=4)
        for combo in [self.status_filter_combo, self.platform_filter_combo, self.genre_filter_combo, self.sort_combo]:
            combo.bind('<<ComboboxSelected>>', lambda _e: self.load_games())

        columns = ('id', 'title', 'platform', 'genre', 'rating', 'status', 'favorite', 'hours')
        self.tree = ttk.Treeview(table_area, columns=columns, show='headings', height=22)
        widths = [45, 240, 140, 120, 70, 110, 75, 85]
        headers = ['ID', 'Title', 'Platform', 'Genre', 'Rating', 'Status', 'Fav', 'Hours']
        for col, head, width in zip(columns, headers, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=width, anchor='center')
        self.tree.column('title', anchor='w')
        self.tree.grid(row=2, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select_game)
        scrollbar = ttk.Scrollbar(table_area, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky='ns')

        ttk.Label(details, text='Game Details', style='Header.TLabel').grid(row=0, column=0, sticky='w')
        self.cover_frame = tk.Frame(details, height=250, width=220, bd=0, highlightthickness=0)
        self.cover_frame.grid(row=1, column=0, sticky='ew', pady=(10, 10))
        self.cover_frame.grid_propagate(False)
        self.cover_label = tk.Label(self.cover_frame, text='No cover selected', anchor='center', justify='center')
        self.cover_label.place(relx=0.5, rely=0.5, anchor='center', relwidth=1.0, relheight=1.0)
        ttk.Label(details, textvariable=self.details_var, justify='left').grid(row=2, column=0, sticky='nw')

        sessions_frame = ttk.LabelFrame(details, text='Recent Sessions', padding=8)
        sessions_frame.grid(row=3, column=0, sticky='nsew', pady=(12, 0))
        sessions_frame.columnconfigure(0, weight=1)
        sessions_frame.rowconfigure(0, weight=1)
        self.sessions_list = tk.Listbox(sessions_frame, height=8, relief='flat', borderwidth=0, highlightthickness=0)
        self.sessions_list.grid(row=0, column=0, sticky='nsew')

    def refresh_reference_data(self):
        platform_rows = self.db.get_platforms()
        genre_rows = self.db.get_genres()
        self.platform_options = {row['name']: row['id'] for row in platform_rows}
        self.genre_options = {row['name']: row['id'] for row in genre_rows}
        platform_values = list(self.platform_options.keys())
        genre_values = list(self.genre_options.keys())
        self.platform_combo.configure(values=platform_values)
        self.genre_combo.configure(values=genre_values)
        self.platform_filter_combo.configure(values=['All'] + platform_values)
        self.genre_filter_combo.configure(values=['All'] + genre_values)
        if platform_values and not self.platform_var.get():
            self.platform_var.set(platform_values[0])
        if genre_values and not self.genre_var.get():
            self.genre_var.set(genre_values[0])

    def _read_form(self) -> Game | None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror('Validation error', 'Title is required.')
            return None
        try:
            rating = int(self.rating_var.get())
            if rating < 1 or rating > 10:
                raise ValueError
        except ValueError:
            messagebox.showerror('Validation error', 'Rating must be between 1 and 10.')
            return None
        year = None
        if self.release_year_var.get().strip():
            try:
                year = int(self.release_year_var.get().strip())
            except ValueError:
                messagebox.showerror('Validation error', 'Release year must be a number.')
                return None
        return Game(
            id=None,
            title=title,
            platform_id=self.platform_options[self.platform_var.get()],
            genre_id=self.genre_options[self.genre_var.get()],
            rating=rating,
            status=self.status_var.get(),
            completed=1 if self.completed_var.get() else 0,
            notes=self.notes_text.get('1.0', 'end').strip(),
            date_added=self.db.now_string(),
            release_year=year,
            publisher=self.publisher_var.get().strip(),
            cover_path=self.cover_path_var.get().strip(),
            favorite=1 if self.favorite_var.get() else 0,
        )

    def add_game(self):
        game = self._read_form()
        if not game:
            return
        self.db.add_game(game)
        self.clear_form()
        self.load_games()

    def update_game(self):
        if self.selected_game_id is None:
            messagebox.showwarning('No selection', 'Select a game first.')
            return
        game = self._read_form()
        if not game:
            return
        self.db.update_game(self.selected_game_id, game)
        self.load_games()

    def delete_game(self):
        if self.selected_game_id is None:
            messagebox.showwarning('No selection', 'Select a game first.')
            return
        if not messagebox.askyesno('Confirm delete', 'Delete selected game and all its sessions?'):
            return
        self.db.delete_game(self.selected_game_id)
        self.selected_game_id = None
        self.clear_form()
        self.load_games()

    def clear_form(self):
        self.title_var.set('')
        self.rating_var.set('8')
        self.status_var.set('Backlog')
        self.completed_var.set(False)
        self.favorite_var.set(False)
        self.release_year_var.set('')
        self.publisher_var.set('')
        self.cover_path_var.set('')
        self.cover_hint_var.set('Use “Import Cover” to copy an image into the project automatically.')
        self.notes_text.delete('1.0', 'end')
        self._update_cover('')

    def clear_cover(self):
        self.cover_path_var.set('')
        self.cover_hint_var.set('Cover removed from the form. The old image file stays in the covers folder.')
        self._update_cover('')

    def reset_filters(self):
        self.search_var.set('')
        self.status_filter_var.set('All')
        self.platform_filter_var.set('All')
        self.genre_filter_var.set('All')
        self.favorite_filter_var.set(False)
        self.sort_var.set('Newest first')
        self.load_games()

    def load_games(self, trigger_refresh: bool = True):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_games(
            search=self.search_var.get(),
            status_filter=self.status_filter_var.get(),
            platform_filter=self.platform_filter_var.get(),
            genre_filter=self.genre_filter_var.get(),
            favorite_only=self.favorite_filter_var.get(),
            sort_by=self.sort_var.get(),
        )
        total_hours = 0.0
        for row in rows:
            hours = round(row['total_minutes'] / 60, 1)
            total_hours += hours
            self.tree.insert('', 'end', values=(
                row['id'], row['title'], row['platform_name'], row['genre_name'], row['rating'],
                row['status'], '★' if row['favorite'] else '', hours,
            ))
        self.stats_var.set(f'{len(rows)} games loaded • {round(total_hours, 1)} hours total')
        if trigger_refresh:
            self.on_data_changed()

    def on_select_game(self, _event=None):
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
        self.favorite_var.set(bool(details['favorite']))
        self.release_year_var.set(str(details['release_year'] or ''))
        self.publisher_var.set(details['publisher'] or '')
        self.cover_path_var.set(details['cover_path'] or '')
        self.cover_hint_var.set('Imported covers are stored in the project’s covers folder.')
        self.notes_text.delete('1.0', 'end')
        self.notes_text.insert('1.0', details['notes'])
        self._refresh_detail_panel(details)
        self.on_game_selected(self.selected_game_id)

    def _refresh_detail_panel(self, details):
        self.details_var.set(
            f"Title: {details['title']}\n"
            f"Platform: {details['platform_name']}\n"
            f"Genre: {details['genre_name']}\n"
            f"Status: {details['status']}\n"
            f"Rating: {details['rating']}/10\n"
            f"Release year: {details['release_year'] or '-'}\n"
            f"Publisher: {details['publisher'] or '-'}\n"
            f"Favorite: {'Yes' if details['favorite'] else 'No'}\n"
            f"Hours played: {round(details['total_minutes'] / 60, 1)}\n"
            f"Sessions: {details['session_count']}\n"
            f"Last session: {details['last_session_date'] or '-'}\n"
            f"Added: {details['date_added']}\n"
            f"Cover: {details['cover_path'] or '-'}"
        )
        self.sessions_list.delete(0, 'end')
        for row in self.db.get_sessions_for_game(details['id']):
            note = f" — {row['notes']}" if row['notes'] else ''
            self.sessions_list.insert('end', f"{row['session_date']} • {row['duration_minutes']} min{note}")
        if self.sessions_list.size() == 0:
            self.sessions_list.insert('end', 'No sessions logged yet.')
        self._update_cover(details['cover_path'])

    def _resolve_cover_path(self, cover_path: str) -> Path | None:
        path = (cover_path or '').strip()
        if not path:
            return None
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        return p

    def _update_cover(self, cover_path: str):
        path = self._resolve_cover_path(cover_path)
        if path is None:
            self.cover_preview = None
            self.cover_label.configure(image='', text='No cover selected')
            return
        if not path.exists():
            self.cover_preview = None
            self.cover_label.configure(image='', text=f'Cover file not found\n{path.name}')
            return
        try:
            image = Image.open(path)
            image = ImageOps.contain(image, (210, 240))
            self.cover_preview = ImageTk.PhotoImage(image)
            self.cover_label.configure(image=self.cover_preview, text='')
        except Exception as exc:
            self.cover_preview = None
            self.cover_label.configure(image='', text=f'Could not open image\n{path.name}\n{exc}')

    def _slugify(self, value: str) -> str:
        value = re.sub(r'[^a-zA-Z0-9]+', '_', value.strip().lower()).strip('_')
        return value or 'cover'

    def browse_cover(self):
        path = filedialog.askopenfilename(title='Select cover image', filetypes=self.IMAGE_FILETYPES)
        if not path:
            return
        source = Path(path)
        extension = source.suffix.lower() or '.png'
        title_slug = self._slugify(self.title_var.get() or source.stem)
        target = self.covers_dir / f'{title_slug}{extension}'
        counter = 2
        while target.exists() and target.resolve() != source.resolve():
            target = self.covers_dir / f'{title_slug}_{counter}{extension}'
            counter += 1
        try:
            shutil.copy2(source, target)
        except Exception as exc:
            messagebox.showerror('Cover import failed', f'Could not copy image:\n{exc}')
            return
        relative = target.relative_to(self.project_root).as_posix()
        self.cover_path_var.set(relative)
        self.cover_hint_var.set(f'Imported successfully: {relative}')
        self._update_cover(relative)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files', '*.csv')], title='Export library to CSV')
        if not path:
            return
        self.db.export_library_csv(path)
        messagebox.showinfo('Export complete', f'Library exported to:\n{path}')

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files', '*.json')], title='Export library to JSON')
        if not path:
            return
        self.db.export_library_json(path)
        messagebox.showinfo('Export complete', f'Library exported to:\n{path}')

    def apply_theme(self, palette: dict[str, str]):
        self.current_palette = palette
        self.notes_text.configure(bg=palette['entry'], fg=palette['fg'], insertbackground=palette['fg'])
        self.sessions_list.configure(
            bg=palette['panel'],
            fg=palette['fg'],
            selectbackground=palette['selected'],
            selectforeground=palette['selected_fg'],
        )
        self.cover_frame.configure(bg=palette['panel'])
        self.cover_label.configure(
            bg=palette['panel'],
            fg=palette['muted'],
            activebackground=palette['panel'],
            activeforeground=palette['muted'],
        )
