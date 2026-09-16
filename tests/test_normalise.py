import pytest
from moveinsync_ota.data.normalise import guard_na, parse_delay_reason, parse_epoch


class TestParseEpoch:
    def test_integer_string(self):
        assert parse_epoch("1746057600") == 1746057600

    def test_float_string(self):
        assert parse_epoch("1746057600.0") == 1746057600

    def test_comma_formatted(self):
        assert parse_epoch("1,746,057,600") == 1746057600

    def test_empty_string(self):
        assert parse_epoch("") is None

    def test_na_lowercase(self):
        assert parse_epoch("na") is None

    def test_null_string(self):
        assert parse_epoch("null") is None

    def test_none_string(self):
        assert parse_epoch("none") is None

    def test_whitespace_na(self):
        assert parse_epoch("  na  ") is None

    def test_non_numeric(self):
        assert parse_epoch("abc") is None

    def test_zero(self):
        assert parse_epoch("0") == 0

    def test_negative(self):
        assert parse_epoch("-1") == -1


class TestParseDelayReason:
    def test_traffic(self):
        assert parse_delay_reason("TRAFFIC") == "TRAFFIC"

    def test_lowercase(self):
        assert parse_delay_reason("traffic") == "TRAFFIC"

    def test_nodelay(self):
        assert parse_delay_reason("NODELAY") == "NODELAY"

    def test_empty_string(self):
        assert parse_delay_reason("") == "UNKNOWN"

    def test_na(self):
        assert parse_delay_reason("na") == "UNKNOWN"

    def test_null(self):
        assert parse_delay_reason("null") == "UNKNOWN"

    def test_none_string(self):
        assert parse_delay_reason("none") == "UNKNOWN"

    def test_whitespace_preserved_after_strip(self):
        assert parse_delay_reason("  TRAFFIC  ") == "TRAFFIC"

    def test_mixed_case(self):
        assert parse_delay_reason("Traffic") == "TRAFFIC"


class TestGuardNa:
    def test_normal_string(self):
        assert guard_na("vendor_abc") == "vendor_abc"

    def test_empty_string(self):
        assert guard_na("") is None

    def test_na(self):
        assert guard_na("na") is None

    def test_null(self):
        assert guard_na("null") is None

    def test_none_string(self):
        assert guard_na("none") is None

    def test_whitespace_only(self):
        # whitespace-only is not in _NA_CLASS after strip; strip returns "" which IS in _NA_CLASS
        assert guard_na("   ") is None

    def test_preserves_content(self):
        assert guard_na("  hello  ") == "hello"
