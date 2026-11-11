"""The app shell: opens the database, builds the screens and switches between them.

Run it from the project root with:   flet run main.py
"""
import os
import sys
from datetime import date
from pathlib import Path

import flet as ft

# Make sure Python can find the "core" folder, wherever the app is started from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from calendar_screen import build_calendar_screen  # noqa: E402
from core.db import get_connection, init_db  # noqa: E402
from goals_screen import build_goals_screen  # noqa: E402
from home_screen import build_home_screen  # noqa: E402
from monthend_screen import build_monthend_screen  # noqa: E402
from setup_screen import build_setup_screen  # noqa: E402


def app_db_path():
    """Where the database file lives."""
    # In a running Flet app this variable points to a private folder that is kept
    # between runs. When it is not set, we fall back to the project folder.
    folder = os.getenv("FLET_APP_STORAGE_DATA")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        return str(Path(folder) / "expense_tracker.db")
    return str(Path(__file__).resolve().parent / "app_data.db")


def main(page: ft.Page):
    page.title = "Expense Tracker"
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT

    db_path = app_db_path()
    conn = get_connection(db_path)
    init_db(conn)
    backup_folder = str(Path(db_path).parent / "backups")

    def today_text():
        return date.today().isoformat()

    screens = {}  # name -> (control, refresh)

    def show(name):
        """Show one screen, hide the others, and refresh the one being shown."""
        for key, (control, refresh) in screens.items():
            control.visible = key == name
        screens[name][1]()
        page.update()

    def go_home(e=None):
        show("home")

    def go_calendar(e=None):
        show("calendar")

    def go_goals(e=None):
        show("goals")

    def go_monthend(e=None):
        show("monthend")

    def go_setup(e=None):
        show("setup")

    screens["home"] = build_home_screen(page, conn, today_text, go_setup)
    screens["calendar"] = build_calendar_screen(page, conn, today_text)
    screens["goals"] = build_goals_screen(page, conn, today_text)
    screens["monthend"] = build_monthend_screen(page, conn, today_text, backup_folder)
    screens["setup"] = build_setup_screen(page, conn, today_text)
    for name in ["calendar", "goals", "monthend", "setup"]:
        screens[name][0].visible = False  # the app starts on the home screen

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Text("Expense Tracker", size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        wrap=True,
                        controls=[
                            ft.Button(content="Home", on_click=go_home),
                            ft.Button(content="Calendar", on_click=go_calendar),
                            ft.Button(content="Goals", on_click=go_goals),
                            ft.Button(content="Month end", on_click=go_monthend),
                            ft.Button(content="Setup", on_click=go_setup),
                        ],
                    ),
                    screens["home"][0],
                    screens["calendar"][0],
                    screens["goals"][0],
                    screens["monthend"][0],
                    screens["setup"][0],
                ],
            )
        )
    )


ft.run(main)