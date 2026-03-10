import tkinter as tk
from tkinter import ttk

from database import DatabaseManager
from ui.dashboard_view import DashboardView
from ui.library_view import LibraryView
from ui.sessions_view import SessionsView
from ui.settings_view import SettingsView
from ui.wishlist_view import WishlistView


class GameVaultApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('GameVault - Stage 5')
        self.root.geometry('1380x860')
        self.root.minsize(1220, 760)

        self.db = DatabaseManager()
        self.db.initialize()
        self.db.seed_if_empty()

        self.style = ttk.Style()
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        self.dashboard = DashboardView(self.notebook, self.db)
        self.sessions = SessionsView(self.notebook, self.db, on_data_changed=self.refresh_all)
        self.wishlist = WishlistView(self.notebook, self.db, on_data_changed=self.refresh_all)
        self.library = LibraryView(
            self.notebook,
            self.db,
            on_data_changed=self.refresh_all,
            on_game_selected=self.on_game_selected,
        )
        self.settings = SettingsView(self.notebook, self.db, on_theme_changed=self.apply_theme)

        self.notebook.add(self.dashboard, text='Dashboard')
        self.notebook.add(self.library, text='Library')
        self.notebook.add(self.sessions, text='Sessions')
        self.notebook.add(self.wishlist, text='Wishlist')
        self.notebook.add(self.settings, text='Settings')

        self.apply_theme(self.db.get_setting('theme', 'dark'))
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.refresh_all()

    def apply_theme(self, theme_name: str) -> None:
        palettes = {
            'dark': {
                'bg': '#1f2430',
                'panel': '#2a3142',
                'panel_2': '#30384c',
                'fg': '#f0f2f5',
                'muted': '#b8c0cc',
                'entry': '#30384c',
                'accent': '#5ea1ff',
                'accent_hover': '#77b0ff',
                'selected': '#3c4b66',
                'selected_fg': '#ffffff',
                'border': '#3b4357',
            },
            'light': {
                'bg': '#f4f6f8',
                'panel': '#ffffff',
                'panel_2': '#edf1f5',
                'fg': '#1b1f23',
                'muted': '#4b5563',
                'entry': '#ffffff',
                'accent': '#246bdb',
                'accent_hover': '#3d7ae0',
                'selected': '#dbeafe',
                'selected_fg': '#111827',
                'border': '#d1d5db',
            },
        }
        p = palettes.get(theme_name, palettes['dark'])
        self.db.set_setting('theme', theme_name)
        self.root.configure(bg=p['bg'])

        self.style.configure('.', background=p['bg'], foreground=p['fg'])
        self.style.configure('TFrame', background=p['bg'])
        self.style.configure('TLabel', background=p['bg'], foreground=p['fg'])
        self.style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), background=p['bg'], foreground=p['fg'])
        self.style.configure('Subtle.TLabel', background=p['bg'], foreground=p['muted'])
        self.style.configure('TLabelFrame', background=p['bg'], foreground=p['fg'], bordercolor=p['border'])
        self.style.configure('TLabelFrame.Label', background=p['bg'], foreground=p['fg'])

        self.style.configure('TNotebook', background=p['bg'], borderwidth=0)
        self.style.configure('TNotebook.Tab', padding=(14, 8), background=p['panel'], foreground=p['fg'])
        self.style.map(
            'TNotebook.Tab',
            background=[('selected', p['accent']), ('active', p['panel_2'])],
            foreground=[('selected', '#ffffff'), ('active', p['fg'])],
        )

        self.style.configure('TButton', background=p['panel'], foreground=p['fg'], borderwidth=1, focusthickness=1, focuscolor=p['accent'])
        self.style.map(
            'TButton',
            background=[('pressed', p['accent']), ('active', p['panel_2'])],
            foreground=[('pressed', '#ffffff'), ('active', p['fg'])],
            relief=[('pressed', 'sunken'), ('!pressed', 'raised')],
        )

        self.style.configure('Accent.TButton', background=p['accent'], foreground='#ffffff', borderwidth=1)
        self.style.map(
            'Accent.TButton',
            background=[('pressed', p['accent']), ('active', p['accent_hover'])],
            foreground=[('pressed', '#ffffff'), ('active', '#ffffff')],
        )

        self.style.configure('TCheckbutton', background=p['bg'], foreground=p['fg'])
        self.style.map('TCheckbutton', background=[('active', p['bg'])], foreground=[('active', p['fg'])])

        self.style.configure('TRadiobutton', background=p['bg'], foreground=p['fg'])
        self.style.map('TRadiobutton', background=[('active', p['bg'])], foreground=[('active', p['fg'])])

        self.style.configure('TEntry', fieldbackground=p['entry'], foreground=p['fg'], insertcolor=p['fg'])
        self.style.map('TEntry', fieldbackground=[('readonly', p['entry'])], foreground=[('readonly', p['fg'])])

        self.style.configure('TSpinbox', fieldbackground=p['entry'], foreground=p['fg'], arrowsize=14)
        self.style.map('TSpinbox', fieldbackground=[('readonly', p['entry'])], foreground=[('readonly', p['fg'])])

        self.style.configure('TCombobox', fieldbackground=p['entry'], background=p['entry'], foreground=p['fg'], arrowcolor=p['fg'])
        self.style.map(
            'TCombobox',
            fieldbackground=[('readonly', p['entry']), ('active', p['entry'])],
            background=[('readonly', p['entry']), ('active', p['entry'])],
            foreground=[('readonly', p['fg']), ('active', p['fg'])],
            arrowcolor=[('readonly', p['fg']), ('active', p['fg'])],
            selectbackground=[('readonly', p['selected'])],
            selectforeground=[('readonly', p['selected_fg'])],
        )

        self.style.configure('Treeview', background=p['panel'], fieldbackground=p['panel'], foreground=p['fg'], rowheight=28, bordercolor=p['border'])
        self.style.map('Treeview', background=[('selected', p['selected'])], foreground=[('selected', p['selected_fg'])])
        self.style.configure('Treeview.Heading', background=p['entry'], foreground=p['fg'])
        self.style.map('Treeview.Heading', background=[('active', p['panel_2'])], foreground=[('active', p['fg'])])

        self.style.configure('Card.TFrame', background=p['panel'])
        self.style.configure('StatTitle.TLabel', background=p['panel'], foreground=p['muted'])
        self.style.configure('StatValue.TLabel', background=p['panel'], foreground=p['fg'], font=('Segoe UI', 18, 'bold'))

        self.root.option_add('*TCombobox*Listbox.background', p['entry'])
        self.root.option_add('*TCombobox*Listbox.foreground', p['fg'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', p['selected'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', p['selected_fg'])

        for view in (self.dashboard, self.library, self.sessions, self.wishlist, self.settings):
            if hasattr(view, 'apply_theme'):
                view.apply_theme(p)

    def on_game_selected(self, game_id: int | None) -> None:
        self.sessions.set_selected_game(game_id)
        self.dashboard.refresh(selected_game_id=game_id)

    def refresh_all(self) -> None:
        self.library.refresh_reference_data()
        self.sessions.refresh_games()
        self.wishlist.refresh_platforms()
        self.dashboard.refresh(selected_game_id=self.library.selected_game_id)
        self.sessions.load_sessions(trigger_refresh=False)
        self.wishlist.load_items(trigger_refresh=False)
        self.library.load_games(trigger_refresh=False)

    def on_close(self) -> None:
        self.db.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    GameVaultApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
