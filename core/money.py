from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

def rupees_to_paise(amount) -> int:
    try:
        value = Decimal(str(amount).strip())
    except InvalidOperation:
        raise ValueError(f"Not a valid amount {amount!r}") from None
    if not value.is_finite():
        raise ValueError(f"Not a valid amount {amount!r}")
    paise = (value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)

def paise_to_rupees_text(paise: int) -> str:
    sign = "-" if paise < 0 else ""
    rupees, remainder = divmod(abs(paise), 100)
    return f"{sign}{rupees:,}.{remainder:02d}"

def check_paise(value, label: str, allow_zero: bool = False) -> None:
    """Raise ValueError unless value is a whole number of paise.

    Positive by default. Pass allow_zero=True to accept zero as well.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be a whole number of paise.")
    if allow_zero and value < 0:
        raise ValueError(f"{label} cannot be negative.")
    if not allow_zero and value <= 0:
        raise ValueError(f"{label} must be greater than zero.")
