import tkinter as tk
from tkinter import ttk

from database import DatabaseManager


class SettingsView(ttk.Frame):
    def __init__(self, parent, db: DatabaseManager, on_theme_changed=None):
        super().__init__(parent, padding=14)
        self.db = db
        self.on_theme_changed = on_theme_changed or (lambda _theme: None)
        self.theme_var = tk.StringVar(value=self.db.get_setting('theme', 'dark'))
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text='Settings', style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 12))
        card = ttk.LabelFrame(self, text='Appearance', padding=16)
        card.grid(row=1, column=0, sticky='nw')
        ttk.Label(card, text='Theme').grid(row=0, column=0, sticky='w')
        theme_box = ttk.Combobox(card, textvariable=self.theme_var, values=['dark', 'light'], state='readonly', width=18)
        theme_box.grid(row=1, column=0, sticky='w', pady=(6, 8))
        ttk.Button(card, text='Apply Theme', command=self.on_apply_clicked).grid(row=2, column=0, sticky='w')
        ttk.Label(card, text='Dark mode gives the app a more polished demo look.', style='Subtle.TLabel').grid(row=3, column=0, sticky='w', pady=(10, 0))

    def on_apply_clicked(self):
        self.on_theme_changed(self.theme_var.get())

    def apply_theme(self, _palette: dict[str, str]):
        pass
