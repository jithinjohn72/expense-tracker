"""The month-end screen: close a finished cycle, see your savings totals, and back up."""
import flet as ft

from core.service import (
    close_oldest_cycle,
    list_backups,
    make_backup,
    month_end_view,
    restore_from_path,
)
from ui_common import money_row, rupees


def build_monthend_screen(page, conn, today_text, backup_folder):
    """Build the month-end screen. Returns (control, refresh)."""
    message = ft.Text("")
    close_box = ft.Column(spacing=8)
    totals_box = ft.Column(spacing=4)
    history_box = ft.Column(spacing=4)
    backups_box = ft.Column(spacing=2)
    restore_field = ft.TextField(label="Path of the backup file to restore")

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

    def close(leftover_action):
        run(lambda: close_oldest_cycle(conn, today_text(), leftover_action), "Cycle closed.")

    def back_up_now(e):
        try:
            path = make_backup(conn, backup_folder, today_text())
        except (ValueError, OSError) as error:
            message.value = str(error)
            message.color = ft.Colors.RED
        else:
            message.value = f"Backup saved: {path}"
            message.color = ft.Colors.GREEN
            refresh()
        page.update()

    def ask_to_restore(e):
        if (restore_field.value or "").strip():
            confirm_box.visible = True
        else:
            message.value = "Type or paste the path of a backup file."
            message.color = ft.Colors.RED
        page.update()

    def cancel_restore(e):
        confirm_box.visible = False
        page.update()

    def do_restore(e):
        confirm_box.visible = False
        run(lambda: restore_from_path(conn, restore_field.value), "Backup restored.")

    confirm_box = ft.Column(
        visible=False,
        spacing=8,
        controls=[
            ft.Text(
                "This replaces ALL the data in the app with the backup. It cannot be undone.",
                color=ft.Colors.RED,
            ),
            ft.Row(
                wrap=True,
                controls=[
                    ft.Button(content="Yes, replace my data", on_click=do_restore),
                    ft.Button(content="Cancel", on_click=cancel_restore),
                ],
            ),
        ],
    )

    def refresh():
        """Read the latest data and refill the screen."""
        view = month_end_view(conn, today_text())

        waiting = view["to_close"]
        if waiting is None:
            current = view["current"]
            if current is not None:
                text = f"The current cycle ends on {current['cycle_end']}. Nothing to close yet."
            else:
                text = "No finished cycle is waiting to be closed."
            close_box.controls = [ft.Text(text)]
        else:
            plan = waiting["plan"]
            left = waiting["summary"]["left_to_spend"]
            label = "Left over" if left >= 0 else "Overspent by"
            close_box.controls = [
                ft.Text(
                    f"Cycle {plan['cycle_start']} to {plan['cycle_end']} has finished.",
                    weight=ft.FontWeight.BOLD,
                ),
                money_row(label, rupees(abs(left)), bold=True),
                ft.Text(
                    "Add to savings: the leftover joins your savings (an overspend is taken "
                    "from them). Carry to next cycle: it moves into the next cycle's pool "
                    "instead. Closing also adds this cycle's set-asides to your goals.",
                    size=12,
                ),
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.Button(content="Add to savings", on_click=lambda e: close("savings")),
                        ft.Button(content="Carry to next cycle", on_click=lambda e: close("carry")),
                    ],
                ),
            ]

        totals = view["totals"]
        totals_box.controls = [
            money_row("Total saved (closed cycles)", rupees(totals["total_saved"]), bold=True),
            money_row("Locked in deposits (never spendable)", rupees(totals["deposits_locked"])),
            money_row("Saved for goals", rupees(totals["saved_for_goals"])),
        ]

        history_rows = []
        for item in view["history"]:
            where = "to savings" if item["action"] == "savings" else "carried over"
            history_rows.append(
                money_row(
                    f"{item['cycle_start']} to {item['cycle_end']}  "
                    f"leftover {rupees(item['leftover'])} {where}",
                    rupees(item["saved"]),
                )
            )
        history_box.controls = history_rows or [ft.Text("No closed cycles yet.")]

        names = list_backups(backup_folder)
        backups_box.controls = [ft.Text(f"Backups are saved in: {backup_folder}", size=12)] + [
            ft.Text(name, size=12) for name in names
        ]
        if not names:
            backups_box.controls.append(ft.Text("No backups yet.", size=12))

    control = ft.Column(
        spacing=8,
        controls=[
            ft.Text("Month end", size=18, weight=ft.FontWeight.BOLD),
            close_box,
            ft.Divider(),
            ft.Text("Savings so far", size=18, weight=ft.FontWeight.BOLD),
            totals_box,
            ft.Text("Closed cycles (amount saved in each)", size=16, weight=ft.FontWeight.BOLD),
            history_box,
            ft.Divider(),
            ft.Text("Backup", size=18, weight=ft.FontWeight.BOLD),
            ft.Button(content="Back up now", on_click=back_up_now),
            backups_box,
            ft.Text("Restore from a backup", size=16, weight=ft.FontWeight.BOLD),
            restore_field,
            ft.Button(content="Restore from this file", on_click=ask_to_restore),
            confirm_box,
            message,
        ],
    )
    refresh()
    return control, refresh