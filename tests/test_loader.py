import io
import csv
import pytest
from moveinsync_ota.data.loader import parse_stream, validate_headers, load_file, REQUIRED_HEADERS
from moveinsync_ota.exceptions import DataLoadError, SchemaValidationError


def make_rows(csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    return list(reader)


HEADER = "product_type,planned_end_epoch,actual_end_epoch,vendor_id,delay_reason"


class TestValidateHeaders:
    def test_all_required_present(self):
        validate_headers(list(REQUIRED_HEADERS))  # no exception

    def test_extra_columns_ok(self):
        validate_headers(list(REQUIRED_HEADERS) + ["extra_col"])  # no exception

    def test_missing_one_header(self):
        headers = list(REQUIRED_HEADERS - {"delay_reason"})
        with pytest.raises(SchemaValidationError, match="delay_reason"):
            validate_headers(headers)

    def test_missing_multiple_headers(self):
        headers = ["product_type", "vendor_id"]
        with pytest.raises(SchemaValidationError):
            validate_headers(headers)

    def test_empty_headers(self):
        with pytest.raises(SchemaValidationError):
            validate_headers([])

    def test_duplicate_required_column_rejected(self):
        headers = list(REQUIRED_HEADERS) + ["vendor_id"]
        with pytest.raises(SchemaValidationError, match="Duplicate"):
            validate_headers(headers)

    def test_duplicate_extra_column_rejected(self):
        headers = list(REQUIRED_HEADERS) + ["extra", "extra"]
        with pytest.raises(SchemaValidationError, match="Duplicate"):
            validate_headers(headers)


class TestParseStreamSpot20Priority:
    """SPOT_2.0 exclusion must fire before epoch checks."""

    def test_spot20_with_null_epoch_counts_as_spot20_excluded(self):
        csv_text = f"{HEADER}\nSPOT_2.0,na,na,V1,NODELAY\n"
        rows = make_rows(csv_text)
        _, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert total == 1
        assert spot20 == 1
        assert null_epoch == 0

    def test_spot20_with_valid_epoch_still_excluded(self):
        csv_text = f"{HEADER}\nSPOT_2.0,1000,1100,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert spot20 == 1
        assert len(vendor_stats) == 0

    def test_non_spot20_passes_through(self):
        csv_text = f"{HEADER}\nSTANDARD,1000,1100,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, _, spot20, _ = parse_stream(rows, "May", 300)
        assert spot20 == 0
        assert "V1" in vendor_stats


class TestParseStreamNullEpochExclusion:
    def test_null_planned_epoch_excluded(self):
        csv_text = f"{HEADER}\nSTANDARD,na,1100,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert null_epoch == 1
        assert len(vendor_stats) == 0

    def test_null_actual_epoch_excluded(self):
        csv_text = f"{HEADER}\nSTANDARD,1000,null,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert null_epoch == 1
        assert len(vendor_stats) == 0

    def test_both_null_epochs_counted_once_each(self):
        csv_text = (
            f"{HEADER}\n"
            "STANDARD,na,1100,V1,NODELAY\n"
            "STANDARD,1000,null,V2,NODELAY\n"
        )
        rows = make_rows(csv_text)
        _, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert total == 2
        assert spot20 == 0
        assert null_epoch == 2


class TestParseStreamOtaClassification:
    def test_ontime_within_T(self):
        # actual_end = planned_end + T exactly -> ontime
        csv_text = f"{HEADER}\nSTANDARD,1000,1300,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, _, _, _ = parse_stream(rows, "May", 300)
        agg = vendor_stats["V1"]
        assert agg.total_count == 1
        assert agg.ontime_count == 1
        assert len(agg.late_delay_reason_counts) == 0

    def test_ontime_before_planned(self):
        csv_text = f"{HEADER}\nSTANDARD,1000,900,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, _, _, _ = parse_stream(rows, "May", 300)
        assert vendor_stats["V1"].ontime_count == 1

    def test_late_one_second_past_T(self):
        # actual_end = planned_end + T + 1 -> late
        csv_text = f"{HEADER}\nSTANDARD,1000,1301,V1,TRAFFIC\n"
        rows = make_rows(csv_text)
        vendor_stats, _, _, _ = parse_stream(rows, "May", 300)
        agg = vendor_stats["V1"]
        assert agg.ontime_count == 0
        assert agg.late_delay_reason_counts["TRAFFIC"] == 1

    def test_late_accumulates_delay_reasons(self):
        csv_text = (
            f"{HEADER}\n"
            "STANDARD,1000,2000,V1,TRAFFIC\n"
            "STANDARD,1000,2000,V1,TRAFFIC\n"
            "STANDARD,1000,2000,V1,NODELAY\n"
        )
        rows = make_rows(csv_text)
        vendor_stats, _, _, _ = parse_stream(rows, "May", 300)
        agg = vendor_stats["V1"]
        assert agg.total_count == 3
        assert agg.ontime_count == 0
        assert agg.late_delay_reason_counts["TRAFFIC"] == 2
        assert agg.late_delay_reason_counts["NODELAY"] == 1


class TestParseStreamVendorAggregation:
    def test_multiple_vendors_tracked_separately(self):
        csv_text = (
            f"{HEADER}\n"
            "STANDARD,1000,1100,V1,NODELAY\n"
            "STANDARD,1000,1100,V2,NODELAY\n"
            "STANDARD,1000,1100,V1,NODELAY\n"
        )
        rows = make_rows(csv_text)
        vendor_stats, total, _, _ = parse_stream(rows, "May", 300)
        assert total == 3
        assert vendor_stats["V1"].total_count == 2
        assert vendor_stats["V2"].total_count == 1

    def test_empty_stream(self):
        vendor_stats, total, spot20, null_epoch = parse_stream([], "May", 300)
        assert total == 0
        assert spot20 == 0
        assert null_epoch == 0
        assert len(vendor_stats) == 0

    def test_period_stored_on_agg(self):
        csv_text = f"{HEADER}\nSTANDARD,1000,1100,V1,NODELAY\n"
        rows = make_rows(csv_text)
        vendor_stats, _, _, _ = parse_stream(rows, "June", 300)
        assert vendor_stats["V1"].period == "June"


class TestParseStreamMixedExclusions:
    def test_mixed_row_types_counted_correctly(self):
        csv_text = (
            f"{HEADER}\n"
            "SPOT_2.0,na,na,V1,NODELAY\n"      # spot20
            "STANDARD,na,1100,V2,NODELAY\n"     # null_epoch (planned)
            "STANDARD,1000,null,V3,NODELAY\n"   # null_epoch (actual)
            "STANDARD,1000,1100,V4,NODELAY\n"   # eligible
        )
        rows = make_rows(csv_text)
        vendor_stats, total, spot20, null_epoch = parse_stream(rows, "May", 300)
        assert total == 4
        assert spot20 == 1
        assert null_epoch == 2
        assert len(vendor_stats) == 1
        assert "V4" in vendor_stats


class TestParseStreamVendorIdValidation:
    def test_blank_vendor_id_raises_data_load_error(self):
        rows = [{"product_type": "STANDARD", "planned_end_epoch": "1000",
                 "actual_end_epoch": "1100", "vendor_id": "", "delay_reason": "NODELAY"}]
        with pytest.raises(DataLoadError, match="vendor_id"):
            parse_stream(rows, "May", 300)

    def test_whitespace_vendor_id_raises_data_load_error(self):
        rows = [{"product_type": "STANDARD", "planned_end_epoch": "1000",
                 "actual_end_epoch": "1100", "vendor_id": "   ", "delay_reason": "NODELAY"}]
        with pytest.raises(DataLoadError, match="vendor_id"):
            parse_stream(rows, "May", 300)

    def test_none_vendor_id_raises_data_load_error(self):
        # csv.DictReader sets field value to None when a row has fewer fields than headers
        rows = [{"product_type": "STANDARD", "planned_end_epoch": "1000",
                 "actual_end_epoch": "1100", "vendor_id": None, "delay_reason": "NODELAY"}]
        with pytest.raises(DataLoadError, match="vendor_id"):
            parse_stream(rows, "May", 300)


class TestLoadFileMissingPath:
    def test_missing_path_raises_data_load_error(self, tmp_path):
        bogus = tmp_path / "nonexistent.csv"
        with pytest.raises(DataLoadError):
            load_file(bogus, "May", 300)
