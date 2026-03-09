import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).with_name('game_collection.db')


class GameCollectionApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Game Collection Manager')
        self.root.geometry('980x620')
        self.root.minsize(900, 560)

        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.create_table()
        self.insert_demo_data_if_empty()

        self.selected_id = None

        self.build_ui()
        self.load_games()
        self.update_stats()

    def create_table(self):
        self.conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                platform TEXT NOT NULL,
                genre TEXT,
                rating INTEGER CHECK(rating >= 0 AND rating <= 10),
                status TEXT NOT NULL DEFAULT 'Backlog',
                completed INTEGER NOT NULL DEFAULT 0,
                date_added TEXT NOT NULL
            )
            '''
        )
        self.conn.commit()

    def insert_demo_data_if_empty(self):
        count = self.conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
        if count > 0:
            return

        demo_rows = [
            ('Elden Ring', 'PC', 'RPG', 10, 'Completed', 1),
            ('Hades', 'Switch', 'Roguelike', 9, 'Playing', 0),
            ('Minecraft', 'PC', 'Sandbox', 8, 'Backlog', 0),
            ('God of War', 'PS5', 'Action', 9, 'Completed', 1),
        ]
        for title, platform, genre, rating, status, completed in demo_rows:
            self.conn.execute(
                '''
                INSERT INTO games (title, platform, genre, rating, status, completed, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (title, platform, genre, rating, status, completed, datetime.now().strftime('%Y-%m-%d %H:%M')),
            )
        self.conn.commit()

    def build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = tk.Label(
            self.root,
            text='Game Collection Manager',
            font=('Segoe UI', 18, 'bold'),
            pady=12,
        )
        header.grid(row=0, column=0, columnspan=2, sticky='ew')

        form = ttk.LabelFrame(self.root, text='Game details', padding=12)
        form.grid(row=1, column=0, sticky='nsw', padx=(12, 6), pady=(0, 12))

        ttk.Label(form, text='Title').grid(row=0, column=0, sticky='w')
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var, width=28).grid(row=1, column=0, sticky='ew', pady=(0, 10))

        ttk.Label(form, text='Platform').grid(row=2, column=0, sticky='w')
        self.platform_var = tk.StringVar()
        platform_box = ttk.Combobox(
            form,
            textvariable=self.platform_var,
            values=['PC', 'PS5', 'PS4', 'Xbox', 'Switch', 'Mobile'],
            state='readonly',
            width=25,
        )
        platform_box.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        platform_box.set('PC')

        ttk.Label(form, text='Genre').grid(row=4, column=0, sticky='w')
        self.genre_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.genre_var, width=28).grid(row=5, column=0, sticky='ew', pady=(0, 10))

        ttk.Label(form, text='Rating (0-10)').grid(row=6, column=0, sticky='w')
        self.rating_var = tk.StringVar(value='8')
        ttk.Spinbox(form, from_=0, to=10, textvariable=self.rating_var, width=8).grid(row=7, column=0, sticky='w', pady=(0, 10))

        ttk.Label(form, text='Status').grid(row=8, column=0, sticky='w')
        self.status_var = tk.StringVar(value='Backlog')
        status_box = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=['Backlog', 'Playing', 'Completed'],
            state='readonly',
            width=25,
        )
        status_box.grid(row=9, column=0, sticky='ew', pady=(0, 10))

        self.completed_var = tk.IntVar(value=0)
        ttk.Checkbutton(form, text='Completed', variable=self.completed_var).grid(row=10, column=0, sticky='w', pady=(0, 12))

        buttons = ttk.Frame(form)
        buttons.grid(row=11, column=0, sticky='ew')
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text='Add', command=self.add_game).grid(row=0, column=0, sticky='ew', padx=(0, 4), pady=2)
        ttk.Button(buttons, text='Update', command=self.update_game).grid(row=0, column=1, sticky='ew', padx=(4, 0), pady=2)
        ttk.Button(buttons, text='Delete', command=self.delete_game).grid(row=1, column=0, sticky='ew', padx=(0, 4), pady=2)
        ttk.Button(buttons, text='Clear', command=self.clear_form).grid(row=1, column=1, sticky='ew', padx=(4, 0), pady=2)

        stats = ttk.LabelFrame(form, text='Quick stats', padding=10)
        stats.grid(row=12, column=0, sticky='ew', pady=(14, 0))
        self.stats_label = ttk.Label(stats, text='Loading...')
        self.stats_label.grid(row=0, column=0, sticky='w')

        right = ttk.Frame(self.root)
        right.grid(row=1, column=1, sticky='nsew', padx=(6, 12), pady=(0, 12))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        topbar = ttk.Frame(right)
        topbar.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        topbar.columnconfigure(1, weight=1)

        ttk.Label(topbar, text='Search').grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(topbar, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky='ew', padx=(0, 10))
        search_entry.bind('<KeyRelease>', lambda event: self.load_games())

        ttk.Label(topbar, text='Filter').grid(row=0, column=2, padx=(0, 6))
        self.filter_var = tk.StringVar(value='All')
        filter_box = ttk.Combobox(
            topbar,
            textvariable=self.filter_var,
            values=['All', 'Completed', 'Not completed'],
            state='readonly',
            width=16,
        )
        filter_box.grid(row=0, column=3)
        filter_box.bind('<<ComboboxSelected>>', lambda event: self.load_games())

        columns = ('id', 'title', 'platform', 'genre', 'rating', 'status', 'completed', 'date_added')
        self.tree = ttk.Treeview(right, columns=columns, show='headings', height=18)
        headings = {
            'id': 'ID',
            'title': 'Title',
            'platform': 'Platform',
            'genre': 'Genre',
            'rating': 'Rating',
            'status': 'Status',
            'completed': 'Completed',
            'date_added': 'Date added',
        }
        widths = {'id': 50, 'title': 220, 'platform': 100, 'genre': 120, 'rating': 70, 'status': 100, 'completed': 90, 'date_added': 130}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor='center' if col != 'title' and col != 'genre' else 'w')

        self.tree.grid(row=1, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        scrollbar = ttk.Scrollbar(right, orient='vertical', command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Label(
            right,
            text=f'Database file: {DB_PATH.name}',
            foreground='gray'
        )
        footer.grid(row=2, column=0, sticky='w', pady=(8, 0))

    def validate_input(self):
        title = self.title_var.get().strip()
        platform = self.platform_var.get().strip()
        genre = self.genre_var.get().strip()
        status = self.status_var.get().strip()

        if not title:
            messagebox.showwarning('Missing data', 'Please enter a game title.')
            return None
        if not platform:
            messagebox.showwarning('Missing data', 'Please choose a platform.')
            return None
        try:
            rating = int(self.rating_var.get())
        except ValueError:
            messagebox.showwarning('Invalid data', 'Rating must be a number from 0 to 10.')
            return None
        if not 0 <= rating <= 10:
            messagebox.showwarning('Invalid data', 'Rating must be between 0 and 10.')
            return None
        return title, platform, genre, rating, status, int(self.completed_var.get())

    def add_game(self):
        data = self.validate_input()
        if not data:
            return
        self.conn.execute(
            '''
            INSERT INTO games (title, platform, genre, rating, status, completed, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (*data, datetime.now().strftime('%Y-%m-%d %H:%M')),
        )
        self.conn.commit()
        self.clear_form()
        self.load_games()
        self.update_stats()

    def update_game(self):
        if self.selected_id is None:
            messagebox.showinfo('No selection', 'Please select a game to update.')
            return
        data = self.validate_input()
        if not data:
            return
        self.conn.execute(
            '''
            UPDATE games
            SET title=?, platform=?, genre=?, rating=?, status=?, completed=?
            WHERE id=?
            ''',
            (*data, self.selected_id),
        )
        self.conn.commit()
        self.load_games()
        self.update_stats()

    def delete_game(self):
        if self.selected_id is None:
            messagebox.showinfo('No selection', 'Please select a game to delete.')
            return
        if not messagebox.askyesno('Confirm delete', 'Delete selected game?'):
            return
        self.conn.execute('DELETE FROM games WHERE id=?', (self.selected_id,))
        self.conn.commit()
        self.clear_form()
        self.load_games()
        self.update_stats()

    def clear_form(self):
        self.selected_id = None
        self.title_var.set('')
        self.platform_var.set('PC')
        self.genre_var.set('')
        self.rating_var.set('8')
        self.status_var.set('Backlog')
        self.completed_var.set(0)
        self.tree.selection_remove(*self.tree.selection())

    def load_games(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = 'SELECT * FROM games WHERE 1=1'
        params = []

        search = self.search_var.get().strip()
        if search:
            query += ' AND (title LIKE ? OR platform LIKE ? OR genre LIKE ? OR status LIKE ?)'
            like = f'%{search}%'
            params.extend([like, like, like, like])

        filter_mode = self.filter_var.get()
        if filter_mode == 'Completed':
            query += ' AND completed=1'
        elif filter_mode == 'Not completed':
            query += ' AND completed=0'

        query += ' ORDER BY title COLLATE NOCASE'

        rows = self.conn.execute(query, params).fetchall()
        for row in rows:
            self.tree.insert(
                '', 'end', iid=row['id'],
                values=(
                    row['id'], row['title'], row['platform'], row['genre'], row['rating'],
                    row['status'], 'Yes' if row['completed'] else 'No', row['date_added']
                )
            )

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = int(selection[0])
        row = self.conn.execute('SELECT * FROM games WHERE id=?', (item_id,)).fetchone()
        if not row:
            return
        self.selected_id = row['id']
        self.title_var.set(row['title'])
        self.platform_var.set(row['platform'])
        self.genre_var.set(row['genre'] or '')
        self.rating_var.set(str(row['rating']))
        self.status_var.set(row['status'])
        self.completed_var.set(row['completed'])

    def update_stats(self):
        total = self.conn.execute('SELECT COUNT(*) FROM games').fetchone()[0]
        completed = self.conn.execute('SELECT COUNT(*) FROM games WHERE completed=1').fetchone()[0]
        avg = self.conn.execute('SELECT ROUND(AVG(rating), 1) FROM games').fetchone()[0]
        avg_text = avg if avg is not None else '-'
        self.stats_label.config(text=f'Total games: {total}\nCompleted: {completed}\nAverage rating: {avg_text}')


if __name__ == '__main__':
    root = tk.Tk()
    style = ttk.Style()
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    elif 'clam' in style.theme_names():
        style.theme_use('clam')
    app = GameCollectionApp(root)
    root.mainloop()
