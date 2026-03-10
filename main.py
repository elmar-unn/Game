import tkinter as tk
from tkinter import ttk

from database import DatabaseManager
from ui.dashboard_view import DashboardView
from ui.library_view import LibraryView
from ui.sessions_view import SessionsView
from ui.wishlist_view import WishlistView


class GameVaultApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('GameVault - Stage 3')
        self.root.geometry('1280x800')
        self.root.minsize(1120, 700)

        self.db = DatabaseManager()
        self.db.initialize()
        self.db.seed_if_empty()

        self._configure_style()

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

        self.notebook.add(self.dashboard, text='Dashboard')
        self.notebook.add(self.library, text='Library')
        self.notebook.add(self.sessions, text='Sessions')
        self.notebook.add(self.wishlist, text='Wishlist')

        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.refresh_all()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TNotebook.Tab', padding=(14, 8))
        style.configure('Treeview', rowheight=28)
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))
        style.configure('Subtle.TLabel', foreground='#444444')

    def on_game_selected(self, game_id: int | None) -> None:
        self.sessions.set_selected_game(game_id)
        self.dashboard.refresh(selected_game_id=game_id)

    def refresh_all(self) -> None:
        if getattr(self, '_refreshing', False):
            return
        self._refreshing = True
        try:
            self.library.refresh_reference_data()
            self.sessions.refresh_games()
            self.wishlist.refresh_platforms()
            self.dashboard.refresh(selected_game_id=self.library.selected_game_id)
            self.sessions.load_sessions(trigger_refresh=False)
            self.wishlist.load_items(trigger_refresh=False)
        finally:
            self._refreshing = False

    def on_close(self) -> None:
        self.db.close()
        self.root.destroy()



def main() -> None:
    root = tk.Tk()
    GameVaultApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
