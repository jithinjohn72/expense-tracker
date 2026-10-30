import pytest

from core.fixed_items import (
    add_fixed_item,
    fixed_totals,
    list_fixed_items,
    set_fixed_active,
    update_fixed_amount,
)


def test_add_returns_id_and_stores_the_row(conn):
    item_id = add_fixed_item(conn, "Rent", "expense", 1500000)
    row = conn.execute("SELECT * FROM fixed_items WHERE id = ?", (item_id,)).fetchone()
    assert row["name"] == "Rent"
    assert row["kind"] == "expense"
    assert row["amount_paise"] == 1500000
    assert row["active"] == 1


def test_name_is_trimmed(conn):
    item_id = add_fixed_item(conn, "  Rent  ", "expense", 100)
    row = conn.execute("SELECT name FROM fixed_items WHERE id = ?", (item_id,)).fetchone()
    assert row["name"] == "Rent"


def test_blank_name_is_rejected(conn):
    with pytest.raises(ValueError):
        add_fixed_item(conn, "   ", "expense", 100)


def test_unknown_kind_is_rejected(conn):
    with pytest.raises(ValueError):
        add_fixed_item(conn, "Rent", "gift", 100)


def test_zero_amount_is_rejected(conn):
    with pytest.raises(ValueError):
        add_fixed_item(conn, "Rent", "expense", 0)


def test_fractional_amount_is_rejected(conn):
    with pytest.raises(ValueError):
        add_fixed_item(conn, "Rent", "expense", 100.5)


def test_duplicate_name_is_rejected(conn):
    add_fixed_item(conn, "Rent", "expense", 100)
    with pytest.raises(ValueError):
        add_fixed_item(conn, "Rent", "expense", 200)


def test_totals_are_split_by_kind(conn):
    add_fixed_item(conn, "Rent", "expense", 1500000)
    add_fixed_item(conn, "Phone EMI", "expense", 500000)
    add_fixed_item(conn, "RD", "deposit", 500000)
    assert fixed_totals(conn) == {"expense": 2000000, "deposit": 500000}


def test_totals_are_zero_when_there_are_no_items(conn):
    assert fixed_totals(conn) == {"expense": 0, "deposit": 0}


def test_inactive_items_are_not_counted(conn):
    item_id = add_fixed_item(conn, "Phone EMI", "expense", 500000)
    set_fixed_active(conn, item_id, False)
    assert fixed_totals(conn)["expense"] == 0


def test_update_amount_changes_the_total(conn):
    item_id = add_fixed_item(conn, "Rent", "expense", 1500000)
    update_fixed_amount(conn, item_id, 1600000)
    assert fixed_totals(conn)["expense"] == 1600000


def test_update_unknown_id_is_rejected(conn):
    with pytest.raises(ValueError):
        update_fixed_amount(conn, 999, 100)


def test_list_hides_inactive_items_by_default(conn):
    add_fixed_item(conn, "Rent", "expense", 100)
    old_id = add_fixed_item(conn, "Old EMI", "expense", 200)
    set_fixed_active(conn, old_id, False)
    assert [row["name"] for row in list_fixed_items(conn)] == ["Rent"]
    assert len(list_fixed_items(conn, active_only=False)) == 2
