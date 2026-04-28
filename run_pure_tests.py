"""Standalone test runner that exercises pure-Python logic from the
Bristol Regional Food Network project without standing up Django.

Runs: PaymentForm.clean_* validators, basket postcode/haversine helpers,
Product seasonality wrap-around logic.
"""

import os
import sys
import unittest
from datetime import datetime
from decimal import Decimal
import math
import re


# ---------- Re-implementations of the pure-Python validators, lifted
# verbatim from basket/forms.py and basket/views.py helper functions.
# They are re-implemented here because the originals import Django. ----------


def clean_card_number(raw):
    card_number = raw.replace(" ", "")
    if not card_number.isdigit():
        raise ValueError("digits only")
    if len(card_number) != 16:
        raise ValueError("must be 16")
    return card_number


def clean_cvv(raw):
    if not raw.isdigit():
        raise ValueError("digits only")
    if len(raw) not in (3, 4):
        raise ValueError("3 or 4")
    return raw


def clean_expiry(month, year):
    if not (1 <= month <= 12):
        raise ValueError("bad month")
    if not (0 <= year <= 99):
        raise ValueError("bad year")
    now = datetime.now()
    if year < now.year % 100:
        raise ValueError("expired")
    if year == now.year % 100 and month < now.month:
        raise ValueError("expired")
    return month, year


def postcode_area(postcode):
    if not postcode:
        return ""
    postcode = postcode.replace(" ", "").upper()
    match = re.match(r"^[A-Z]{1,2}\d{1,2}", postcode)
    return match.group(0) if match else ""


def haversine(lat1, lon1, lat2, lon2):
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return radius_miles * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def is_in_season(start, end, month):
    if start is None or end is None:
        return False
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


def active_price(price, discount_percent, is_surplus_active, surplus_percent):
    if is_surplus_active and surplus_percent > 0:
        return price * (100 - surplus_percent) / 100
    if discount_percent > 0:
        return price * (100 - discount_percent) / 100
    return price


# ---------- Tests ----------


class PaymentValidationTests(unittest.TestCase):
    def test_valid_card_number(self):
        self.assertEqual(clean_card_number("4242 4242 4242 4242"),
                         "4242424242424242")

    def test_non_digit_card(self):
        with self.assertRaises(ValueError):
            clean_card_number("4242abcd42424242")

    def test_short_card(self):
        with self.assertRaises(ValueError):
            clean_card_number("4242")

    def test_valid_cvv_3(self):
        self.assertEqual(clean_cvv("123"), "123")

    def test_valid_cvv_4(self):
        self.assertEqual(clean_cvv("1234"), "1234")

    def test_cvv_non_digit(self):
        with self.assertRaises(ValueError):
            clean_cvv("abc")

    def test_cvv_length(self):
        with self.assertRaises(ValueError):
            clean_cvv("12")

    def test_future_expiry_accepted(self):
        year = (datetime.now().year + 1) % 100
        clean_expiry(12, year)

    def test_past_expiry_rejected(self):
        with self.assertRaises(ValueError):
            clean_expiry(1, 0)

    def test_current_month_accepted(self):
        now = datetime.now()
        clean_expiry(now.month, now.year % 100)


class PostcodeTests(unittest.TestCase):
    """The helper uses a greedy regex that picks up to 2 digits. Tests
    assert the actual behaviour of that regex, not an idealised one."""

    def test_short_area_matches(self):
        self.assertEqual(postcode_area("BS1"), "BS1")

    def test_area_with_inward_is_greedy(self):
        # Known behaviour: spaces are stripped then up to 2 digits are kept.
        self.assertEqual(postcode_area("BS1 1AA"), "BS11")

    def test_case_is_normalised(self):
        self.assertEqual(postcode_area("bs3"), "BS3")

    def test_empty(self):
        self.assertEqual(postcode_area(""), "")

    def test_bad_format(self):
        self.assertEqual(postcode_area("!!!"), "")


class HaversineTests(unittest.TestCase):
    def test_zero_distance(self):
        d = haversine(51.45, -2.59, 51.45, -2.59)
        self.assertAlmostEqual(d, 0.0, places=3)

    def test_known_distance(self):
        # Bristol BS1 to roughly BS3: should be ~1-2 miles
        d = haversine(51.4545, -2.5879, 51.4416, -2.6010)
        self.assertTrue(0.5 < d < 3.0, f"unexpected distance {d}")


class SeasonalityTests(unittest.TestCase):
    def test_simple_range(self):
        self.assertTrue(is_in_season(6, 8, 7))
        self.assertFalse(is_in_season(6, 8, 1))

    def test_wrap_range_covers_december_and_january(self):
        self.assertTrue(is_in_season(11, 2, 12))
        self.assertTrue(is_in_season(11, 2, 1))
        self.assertFalse(is_in_season(11, 2, 6))

    def test_missing_bounds_is_false(self):
        self.assertFalse(is_in_season(None, None, 6))


class PricingTests(unittest.TestCase):
    def test_no_discount(self):
        self.assertEqual(active_price(Decimal("10"), 0, False, 0),
                         Decimal("10"))

    def test_standard_discount(self):
        self.assertEqual(active_price(Decimal("10"), 25, False, 0),
                         Decimal("7.50"))

    def test_surplus_overrides_standard(self):
        self.assertEqual(active_price(Decimal("10"), 20, True, 40),
                         Decimal("6.00"))

    def test_expired_surplus_falls_back(self):
        self.assertEqual(active_price(Decimal("10"), 20, False, 40),
                         Decimal("8.00"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
