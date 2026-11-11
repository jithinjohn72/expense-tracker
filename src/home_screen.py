"""The home screen: today's limit, the money buckets, today's entries and a quick-add form."""
import flet as ft

from core.service import add_spending_today, home_view
from ui_common import money_row, rupees


def build_summary(view, on_go_setup):
    """Turn the data from home_view into a list of controls."""
    if view is None:
        return [
            ft.Text("No pay cycle covers today yet."),
            ft.Button(content="Go to Setup to start one", on_click=on_go_setup),
        ]

    limit = view["limit"]
    summary = view["summary"]
    plan = view["plan"]
    left_color = ft.Colors.RED if limit["left_today"] < 0 else None

    today_card = ft.Container(
        padding=16,
        border_radius=12,
        bgcolor=ft.Colors.BLUE_50,
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text("You can spend today", size=16),
                ft.Text(rupees(limit["limit"]), size=36, weight=ft.FontWeight.BOLD),
                ft.Text(f"Spent today {rupees(limit['spent_today'])}"),
                ft.Text(f"Left today {rupees(limit['left_today'])}", color=left_color),
                ft.Text(f"{limit['days_left']} days left in this cycle"),
            ],
        ),
    )

    controls = [
        today_card,
        ft.Text(f"Cycle: {plan['cycle_start']} to {plan['cycle_end']}", size=12),
        money_row("Salary", rupees(summary["salary"])),
        money_row("Extra credited (goes to the pool)", rupees(summary["extra_credits"])),
        money_row("Carried in from last cycle", rupees(summary["carried_in"])),
        money_row("Locked deposits (not spendable)", rupees(summary["locked_deposits"])),
        money_row("Fixed expenses", rupees(summary["fixed_expenses"])),
        money_row("Reserved savings", rupees(summary["reserved_savings"])),
        money_row("Goal set-asides", rupees(summary["set_asides"])),
        ft.Divider(),
        money_row("Spendable pool", rupees(summary["spendable_pool"]), bold=True),
        money_row("Spent so far", rupees(summary["spent"])),
        money_row("Left to spend", rupees(summary["left_to_spend"]), bold=True),
        ft.Divider(),
        ft.Text("Today's entries", size=18, weight=ft.FontWeight.BOLD),
    ]
    if not view["entries"]:
        controls.append(ft.Text("Nothing recorded today."))
    for entry in view["entries"]:
        controls.append(
            money_row(
                f"{entry['category']}  {entry['description']}", rupees(entry["amount_paise"])
            )
        )
    return controls


def build_home_screen(page, conn, today_text, on_go_setup):
    """Build the home screen. Returns (control, refresh)."""
    summary_box = ft.Column(spacing=8)
    message = ft.Text("", color=ft.Colors.RED)
    amount_field = ft.TextField(label="Amount in rupees", keyboard_type=ft.KeyboardType.NUMBER)
    note_field = ft.TextField(label="What was it for? (optional)")
    category_field = ft.TextField(label="Category, for example food (optional)")

    def refresh():
        """Read the latest numbers and refill the summary area."""
        summary_box.controls = build_summary(home_view(conn, today_text()), on_go_setup)

    def add_spending(e):
        message.value = ""
        try:
            add_spending_today(
                conn,
                today_text(),
                amount_field.value or "",
                note_field.value or "",
                category_field.value or "",
            )
        except ValueError as error:
            message.value = str(error)  # shown in red under the form
        else:
            amount_field.value = ""
            note_field.value = ""
            category_field.value = ""
            refresh()
        page.update()

    control = ft.Column(
        controls=[
            summary_box,
            ft.Divider(),
            ft.Text("Add spending", size=18, weight=ft.FontWeight.BOLD),
            amount_field,
            note_field,
            category_field,
            ft.Button(content="Add spending", on_click=add_spending),
            message,
        ],
    )
    refresh()
    return control, refresh