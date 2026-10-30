
import pytest

from core.money import paise_to_rupees_text, rupees_to_paise, check_paise


def test_whole_rupees_convert_to_paise():
    assert rupees_to_paise(250) == 25000


def test_decimal_text_converts_exactly():
    assert rupees_to_paise("250.50") == 25050


def test_float_rounding_error_does_not_leak():
    assert rupees_to_paise(0.1 + 0.2) == 30


def test_extra_decimals_round_half_up():
    assert rupees_to_paise("10.005") == 1001


def test_invalid_text_is_rejected():
    with pytest.raises(ValueError):
        rupees_to_paise("abc")


def test_nan_is_rejected():
    with pytest.raises(ValueError):
        rupees_to_paise("nan")


def test_paise_to_text_adds_commas():
    assert paise_to_rupees_text(1500050) == "15,000.50"


def test_paise_to_text_pads_small_amounts():
    assert paise_to_rupees_text(5) == "0.05"


def test_negative_amounts_keep_their_sign():
    assert paise_to_rupees_text(-2550) == "-25.50"
    
def test_check_paise_accepts_a_positive_whole_number():
    check_paise(100, "Amount")  # should not raise


def test_check_paise_rejects_zero_unless_allowed():
    with pytest.raises(ValueError):
        check_paise(0, "Amount")
    check_paise(0, "Amount", allow_zero=True)  # should not raise


def test_check_paise_rejects_negative_numbers():
    with pytest.raises(ValueError):
        check_paise(-1, "Amount")
    with pytest.raises(ValueError):
        check_paise(-1, "Amount", allow_zero=True)


def test_check_paise_rejects_floats_and_booleans():
    with pytest.raises(ValueError):
        check_paise(10.5, "Amount")
    with pytest.raises(ValueError):
        check_paise(True, "Amount")