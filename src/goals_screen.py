"""The goals screen: purchase goals with their progress, and a form to add one."""
import flet as ft

from core.service import add_goal_from_text, goals_view, switch_goal, top_up_goal
from ui_common import rupees


def build_goals_screen(page, conn, today_text):
    """Build the goals screen. Returns (control, refresh)."""
    message = ft.Text("")
    cycle_note = ft.Text("", size=12)
    summary_text = ft.Text("", size=12)
    goals_box = ft.Column(spacing=8)
    number = ft.KeyboardType.NUMBER

    name_field = ft.TextField(label="What are you saving for? (for example Laptop)")
    price_field = ft.TextField(label="Price in rupees", keyboard_type=number)
    date_field = ft.TextField(label="Buy it by (YYYY-MM-DD)")
    saved_field = ft.TextField(label="Already saved in rupees (optional)", keyboard_type=number)

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

    def add_new_goal(e):
        def action():
            add_goal_from_text(
                conn,
                name_field.value,
                price_field.value,
                date_field.value,
                saved_field.value,
            )
            name_field.value = ""
            price_field.value = ""
            date_field.value = ""
            saved_field.value = ""

        run(action, "Goal added.")

    def goal_card(goal):
        """One goal: its name, a switch, a progress bar, the numbers, and a way to add savings."""
        top_up_box = ft.TextField(label="Add saved money", width=170, keyboard_type=number)

        def top_up(e, goal_id=goal["id"], box=top_up_box):
            run(lambda: top_up_goal(conn, goal_id, box.value), "Saved amount updated.")

        def toggle(e, goal_id=goal["id"]):
            run(lambda: switch_goal(conn, goal_id, e.control.value), "Updated.")

        percent = int(goal["progress"] * 100)
        if goal["active"]:
            plan_line = f"Set aside this cycle: {rupees(goal['set_aside'])}"
        else:
            plan_line = "Switched off: nothing is set aside for this goal."
        return ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(goal["name"], expand=True, size=16, weight=ft.FontWeight.BOLD),
                        ft.Switch(label="Active", value=goal["active"], on_change=toggle),
                    ]
                ),
                ft.ProgressBar(value=goal["progress"]),
                ft.Text(
                    f"{rupees(goal['saved'])} of {rupees(goal['price'])} ({percent}%), "
                    f"to buy by {goal['target_date']}"
                ),
                ft.Text(plan_line),
                ft.Row(
                    wrap=True,
                    controls=[top_up_box, ft.Button(content="Add to saved", on_click=top_up)],
                ),
                ft.Divider(),
            ],
        )

    def refresh():
        """Read the latest data and refill the screen."""
        view = goals_view(conn, today_text())
        if view["plan"] is None:
            cycle_note.value = "No pay cycle covers today, so nothing is being set aside yet."
        else:
            cycle_note.value = "Money set aside for goals lowers your daily limit."
        summary_text.value = (
            f"Set aside this cycle {rupees(view['total_set_aside'])}   "
            f"Saved for goals so far {rupees(view['saved_for_goals'])}"
        )
        goals_box.controls = [goal_card(goal) for goal in view["goals"]] or [
            ft.Text("No goals yet. Add one below.")
        ]

    control = ft.Column(
        spacing=8,
        controls=[
            ft.Text("Purchase goals", size=18, weight=ft.FontWeight.BOLD),
            cycle_note,
            summary_text,
            goals_box,
            ft.Text("Add a goal", size=16, weight=ft.FontWeight.BOLD),
            name_field,
            price_field,
            date_field,
            saved_field,
            ft.Button(content="Add goal", on_click=add_new_goal),
            message,
        ],
    )
    refresh()
    return control, refresh