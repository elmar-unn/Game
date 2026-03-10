import tkinter as tk
from tkinter import messagebox, ttk

from database import DatabaseManager
from models import WishlistItem


class WishlistView(ttk.Frame):
    PRIORITIES = ['High', 'Medium', 'Low']

    def __init__(self, parent: tk.Misc, db: DatabaseManager, on_data_changed=None):
        super().__init__(parent, padding=14)
        self.db = db
        self.on_data_changed = on_data_changed or (lambda: None)
        self.platform_options: dict[str, int] = {}
        self.selected_item_id: int | None = None

        self.title_var = tk.StringVar()
        self.platform_var = tk.StringVar()
        self.priority_var = tk.StringVar(value='Medium')
        self.summary_var = tk.StringVar(value='0 items loaded')

        self._build_ui()
        self.refresh_platforms()
        self.load_items(trigger_refresh=False)

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        form = ttk.LabelFrame(self, text='Add Wishlist Item', padding=14)
        form.grid(row=0, column=0, sticky='ns')
        table = ttk.Frame(self)
        table.grid(row=0, column=1, sticky='nsew', padx=(16, 0))
        table.columnconfigure(0, weight=1)
        table.rowconfigure(2, weight=1)

        ttk.Label(form, text='Wishlist', style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 12))
        ttk.Label(form, text='Title').grid(row=1, column=0, sticky='w')
        ttk.Entry(form, textvariable=self.title_var, width=30).grid(row=2, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Platform').grid(row=3, column=0, sticky='w')
        self.platform_combo = ttk.Combobox(form, textvariable=self.platform_var, state='readonly', width=28)
        self.platform_combo.grid(row=4, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(form, text='Priority').grid(row=5, column=0, sticky='w')
        ttk.Combobox(form, textvariable=self.priority_var, values=self.PRIORITIES, state='readonly', width=28).grid(row=6, column=0, sticky='ew', pady=(0, 8))
        ttk.Button(form, text='Add to Wishlist', command=self.add_item).grid(row=7, column=0, sticky='ew', pady=4)
        ttk.Button(form, text='Delete Selected', command=self.delete_item).grid(row=8, column=0, sticky='ew', pady=4)

        ttk.Label(table, text='Wishlist Items', style='Header.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(table, textvariable=self.summary_var, style='Subtle.TLabel').grid(row=1, column=0, sticky='w', pady=(2, 8))
        columns = ('id', 'title', 'platform', 'priority', 'added')
        self.tree = ttk.Treeview(table, columns=columns, show='headings', height=18)
        widths = [45, 260, 140, 90, 140]
        headers = ['ID', 'Title', 'Platform', 'Priority', 'Added']
        for col, head, width in zip(columns, headers, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=width, anchor='center')
        self.tree.column('title', anchor='w')
        self.tree.grid(row=2, column=0, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        scrollbar = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky='ns')

    def refresh_platforms(self):
        rows = self.db.get_platforms()
        self.platform_options = {row['name']: row['id'] for row in rows}
        values = list(self.platform_options.keys())
        self.platform_combo.configure(values=values)
        if values and not self.platform_var.get():
            self.platform_var.set(values[0])

    def load_items(self, trigger_refresh: bool = True):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_wishlist()
        for row in rows:
            self.tree.insert('', 'end', values=(row['id'], row['title'], row['platform_name'], row['priority'], row['added_at']))
        priority_counts = {'High': 0, 'Medium': 0, 'Low': 0}
        for row in rows:
            priority_counts[row['priority']] += 1
        self.summary_var.set(f"{len(rows)} items • High: {priority_counts['High']} • Medium: {priority_counts['Medium']} • Low: {priority_counts['Low']}")
        if trigger_refresh:
            self.on_data_changed()

    def add_item(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror('Validation error', 'Title is required.')
            return
        item = WishlistItem(None, title, self.platform_options[self.platform_var.get()], self.priority_var.get(), self.db.now_string())
        self.db.add_wishlist_item(item)
        self.title_var.set('')
        self.load_items()

    def delete_item(self):
        if self.selected_item_id is None:
            messagebox.showwarning('No selection', 'Select a wishlist item first.')
            return
        if not messagebox.askyesno('Confirm delete', 'Delete selected wishlist item?'):
            return
        self.db.delete_wishlist_item(self.selected_item_id)
        self.selected_item_id = None
        self.load_items()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], 'values')
        self.selected_item_id = int(values[0])

    def apply_theme(self, _palette: dict[str, str]):
        pass
