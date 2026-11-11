"""The setup screen: this cycle's salary and savings goal, and the fixed items."""
import flet as ft

from core.money import paise_to_plain_text
from core.service import (
    add_fixed,
    change_fixed_amount,
    change_salary,
    change_savings_goal,
    seed_demo_data,
    setup_view,
    start_cycle,
    switch_fixed,
)
from ui_common import rupees


def build_setup_screen(page, conn, today_text):
    """Build the setup screen. Returns (control, refresh)."""
    state = {"plan_id": None}  # filled in by refresh(): the cycle that covers today

    message = ft.Text("")
    cycle_text = ft.Text("")
    totals_text = ft.Text("", size=12)
    items_box = ft.Column(spacing=8)
    number = ft.KeyboardType.NUMBER

    salary_day_field = ft.TextField(label="Salary day of the month (1 to 28)", keyboard_type=number)
    salary_field = ft.TextField(label="Salary in rupees", keyboard_type=number)
    savings_field = ft.TextField(label="Extra savings goal in rupees (optional)", keyboard_type=number)
    name_field = ft.TextField(label="Name, for example Rent or RD")
    item_amount_field = ft.TextField(label="Amount in rupees", keyboard_type=number)

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

    def start_this_cycle(e):
        run(
            lambda: start_cycle(
                conn,
                today_text(),
                salary_day_field.value,
                salary_field.value,
                savings_field.value,
            ),
            "Cycle started.",
        )

    def load_demo(e):
        run(lambda: seed_demo_data(conn, today_text()), "Demo data loaded.")

    def save_salary(e):
        run(lambda: change_salary(conn, state["plan_id"], salary_field.value), "Salary saved.")

    def save_savings(e):
        run(
            lambda: change_savings_goal(conn, state["plan_id"], savings_field.value),
            "Savings goal saved.",
        )

    def add_item(kind):
        def action():
            add_fixed(conn, name_field.value, kind, item_amount_field.value)
            name_field.value = ""
            item_amount_field.value = ""

        run(action, "Item added.")

    def item_row(item):
        """One fixed item: its name and kind, an on/off switch, and an amount you can change."""
        amount_box = ft.TextField(
            label="Amount", value=paise_to_plain_text(item["amount_paise"]), width=160
        )

        def save_amount(e, item_id=item["id"], box=amount_box):
            run(lambda: change_fixed_amount(conn, item_id, box.value), "Amount saved.")

        def toggle(e, item_id=item["id"]):
            run(lambda: switch_fixed(conn, item_id, e.control.value), "Updated.")

        return ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            f"{item['name']} ({item['kind']})",
                            expand=True,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Switch(label="Active", value=bool(item["active"]), on_change=toggle),
                    ]
                ),
                ft.Row(
                    controls=[amount_box, ft.Button(content="Save amount", on_click=save_amount)]
                ),
                ft.Divider(),
            ],
        )

    new_cycle_box = ft.Column(
        spacing=8,
        controls=[
            salary_day_field,
            ft.Row(
                wrap=True,
                controls=[
                    ft.Button(content="Start this cycle", on_click=start_this_cycle),
                    ft.Button(content="Load demo data", on_click=load_demo),
                ],
            ),
        ],
    )
    edit_cycle_box = ft.Row(
        wrap=True,
        controls=[
            ft.Button(content="Save salary", on_click=save_salary),
            ft.Button(content="Save savings goal", on_click=save_savings),
        ],
    )

    def refresh():
        """Read the latest data and refill the screen."""
        view = setup_view(conn, today_text())
        plan = view["plan"]
        state["plan_id"] = plan["id"] if plan is not None else None
        if plan is not None:
            cycle_text.value = f"Current cycle: {plan['cycle_start']} to {plan['cycle_end']}"
            salary_field.value = paise_to_plain_text(plan["salary_paise"])
            savings_field.value = paise_to_plain_text(plan["savings_goal_paise"])
        else:
            defaults = view["defaults"]
            cycle_text.value = "No pay cycle covers today. Start one below."
            salary_day_field.value = defaults["salary_day"]
            salary_field.value = defaults["salary"]
            savings_field.value = defaults["savings_goal"]
        new_cycle_box.visible = plan is None
        edit_cycle_box.visible = plan is not None
        totals = view["totals"]
        totals_text.value = (
            f"Active fixed expenses {rupees(totals['expense'])}   "
            f"Locked deposits {rupees(totals['deposit'])}"
        )
        items_box.controls = [item_row(item) for item in view["fixed_items"]] or [
            ft.Text("No fixed items yet.")
        ]

    control = ft.Column(
        spacing=8,
        controls=[
            ft.Text("This pay cycle", size=18, weight=ft.FontWeight.BOLD),
            cycle_text,
            salary_field,
            savings_field,
            new_cycle_box,
            edit_cycle_box,
            ft.Divider(),
            ft.Text("Fixed items", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Paid at the start of the month. Deposits are locked and never spendable.",
                size=12,
            ),
            totals_text,
            items_box,
            ft.Text("Add a fixed item", size=16, weight=ft.FontWeight.BOLD),
            name_field,
            item_amount_field,
            ft.Row(
                wrap=True,
                controls=[
                    ft.Button(content="Add as expense", on_click=lambda e: add_item("expense")),
                    ft.Button(content="Add as deposit", on_click=lambda e: add_item("deposit")),
                ],
            ),
            message,
        ],
    )
    refresh()
    return control, refresh
