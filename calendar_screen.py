"""The calendar screen: a grid of the pay cycle's days, and the entries of the chosen day."""
import flet as ft

from core.money import paise_to_plain_text
from core.service import (
    add_entry_on_day,
    calendar_view,
    change_entry_amount,
    day_view,
    remove_entry,
)
from ui_common import money_row, rupees, short_rupees

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CELL = 40  # the width of one day in the grid


def build_calendar_screen(page, conn, today_text):
    """Build the calendar screen. Returns (control, refresh)."""
    # anchor: any date inside the cycle being shown. selected: the day whose entries are open.
    state = {"anchor": None, "selected": None, "previous": None, "next": None}

    message = ft.Text("")
    title_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    grid_box = ft.Column(spacing=4)
    categories_box = ft.Column(spacing=4)
    day_title = ft.Text("", size=18, weight=ft.FontWeight.BOLD)
    entries_box = ft.Column(spacing=8)
    amount_field = ft.TextField(label="Amount in rupees", keyboard_type=ft.KeyboardType.NUMBER)
    note_field = ft.TextField(label="What was it for? (optional)")
    category_field = ft.TextField(label="Category, for example food (optional)")

    def run(action, done):
        """Run an action. Show a green note on success, or the error in red, then refresh."""
        try:
            action()
        except ValueError as error:
            message.value = str(error)
            message.color = ft.Colors.RED
        else:
            message.value = done
            message.color = ft.Colors.GREEN
            refresh()
        page.update()

    def select_day(day):
        state["selected"] = day
        message.value = ""
        refresh()
        page.update()

    def go_to_cycle(anchor):
        state["anchor"] = anchor
        state["selected"] = anchor
        message.value = ""
        refresh()
        page.update()

    previous_button = ft.Button(
        content="< Previous cycle", on_click=lambda e: go_to_cycle(state["previous"])
    )
    next_button = ft.Button(content="Next cycle >", on_click=lambda e: go_to_cycle(state["next"]))

    def day_cell(day, selected):
        """One square of the grid: the day number, what was spent, and any extra money."""
        if day is None:
            return ft.Container(width=CELL, height=CELL + 24)
        if day["date"] == selected:
            background = ft.Colors.BLUE_100
        elif day["spent"]:
            background = ft.Colors.ORANGE_50
        elif day["credited"]:
            background = ft.Colors.GREEN_50
        else:
            background = None
        number_color = ft.Colors.BLUE_700 if day["is_today"] else None
        credit_text = "+" + short_rupees(day["credited"]) if day["credited"] else ""
        return ft.Container(
            width=CELL,
            height=CELL + 24,
            padding=3,
            border_radius=6,
            bgcolor=background,
            on_click=lambda e, chosen=day["date"]: select_day(chosen),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Text(str(day["day"]), size=13, weight=ft.FontWeight.BOLD, color=number_color),
                    ft.Text(short_rupees(day["spent"]), size=10),
                    ft.Text(credit_text, size=10, color=ft.Colors.GREEN_700),
                ],
            ),
        )

    def entry_row(entry):
        """One entry: what it was, its amount, and boxes to change or delete it."""
        is_credit = entry["direction"] == "credit"
        sign = "+" if is_credit else "-"
        label = f"{entry['category']}  {entry['description']}".strip()
        amount_box = ft.TextField(
            label="Amount", value=paise_to_plain_text(entry["amount_paise"]), width=140
        )

        def save_amount(e, txn_id=entry["id"], box=amount_box):
            run(lambda: change_entry_amount(conn, txn_id, box.value), "Amount saved.")

        def delete(e, txn_id=entry["id"]):
            run(lambda: remove_entry(conn, txn_id), "Entry deleted.")

        return ft.Column(
            spacing=4,
            controls=[
                money_row(label, f"{sign}{rupees(entry['amount_paise'])}"),
                ft.Row(
                    wrap=True,
                    controls=[
                        amount_box,
                        ft.Button(content="Save amount", on_click=save_amount),
                        ft.Button(content="Delete", on_click=delete),
                    ],
                ),
                ft.Divider(),
            ],
        )

    def add_entry(kind):
        def action():
            add_entry_on_day(
                conn,
                state["selected"],
                kind,
                amount_field.value,
                note_field.value,
                category_field.value,
            )
            amount_field.value = ""
            note_field.value = ""
            category_field.value = ""

        run(action, "Entry added.")

    day_panel = ft.Column(
        spacing=8,
        controls=[
            ft.Divider(),
            day_title,
            entries_box,
            ft.Text("Add to this day", size=16, weight=ft.FontWeight.BOLD),
            amount_field,
            note_field,
            category_field,
            ft.Row(
                wrap=True,
                controls=[
                    ft.Button(content="Add spending", on_click=lambda e: add_entry("spending")),
                    ft.Button(content="Add extra money", on_click=lambda e: add_entry("credit")),
                ],
            ),
        ],
    )

    def refresh():
        """Read the latest data and redraw the grid and the chosen day."""
        today = today_text()
        if state["anchor"] is None:
            state["anchor"] = today
        view = calendar_view(conn, state["anchor"], today)
        if view is None and state["anchor"] != today:
            state["anchor"] = today  # fall back to the cycle that covers today
            view = calendar_view(conn, today, today)
        if view is None:
            title_text.value = "No pay cycle covers this date. Start one in Setup."
            grid_box.controls = []
            categories_box.controls = []
            day_panel.visible = False
            previous_button.visible = False
            next_button.visible = False
            return

        plan = view["plan"]
        inside = plan["cycle_start"] <= (state["selected"] or "") <= plan["cycle_end"]
        if not inside:
            covers_today = plan["cycle_start"] <= today <= plan["cycle_end"]
            state["selected"] = today if covers_today else plan["cycle_start"]
        state["previous"] = view["previous_anchor"]
        state["next"] = view["next_anchor"]
        previous_button.visible = view["previous_anchor"] is not None
        next_button.visible = view["next_anchor"] is not None

        title_text.value = f"Cycle {plan['cycle_start']} to {plan['cycle_end']}"
        header = ft.Row(
            spacing=4, controls=[ft.Text(name, width=CELL, size=11) for name in WEEKDAYS]
        )
        grid_box.controls = [header] + [
            ft.Row(spacing=4, controls=[day_cell(slot, state["selected"]) for slot in week])
            for week in view["weeks"]
        ]

        category_rows = [money_row(name, rupees(total)) for name, total in view["categories"].items()]
        categories_box.controls = [
            ft.Text("Spent by category", size=16, weight=ft.FontWeight.BOLD)
        ] + (category_rows or [ft.Text("No spending yet.")])

        entries = day_view(conn, state["selected"])["entries"]
        day_title.value = f"Entries for {state['selected']}"
        entries_box.controls = [entry_row(entry) for entry in entries] or [
            ft.Text("Nothing recorded this day.")
        ]
        day_panel.visible = True

    control = ft.Column(
        spacing=8,
        controls=[
            title_text,
            ft.Row(wrap=True, controls=[previous_button, next_button]),
            grid_box,
            categories_box,
            day_panel,
            message,
        ],
    )
    refresh()
    return control, refresh