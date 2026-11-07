"""Small helpers shared by the screens."""
import flet as ft

from core.money import paise_to_rupees_text


def rupees(paise):
    """Format paise as text with a rupee sign, e.g. 1500000 -> '₹ 15,000.00'."""
    return f"₹ {paise_to_rupees_text(paise)}"


def money_row(label, value, bold=False):
    """One line of a list: a label on the left and an amount on the right."""
    weight = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
    return ft.Row(
        controls=[
            ft.Text(label, expand=True, weight=weight),
            ft.Text(value, weight=weight),
        ]
    )
    
def short_rupees(paise):
    """Whole rupees with commas, for tight spaces: 1234567 -> '12,345'. Zero gives ''."""
    if paise == 0:
        return ""
    return f"{paise // 100:,}"