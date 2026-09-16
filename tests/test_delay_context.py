"""Unit tests for compute.delay_context — build_delay_context and nodelay_dominates."""
from collections import Counter

import pytest

from moveinsync_ota.compute.delay_context import build_delay_context
from moveinsync_ota.data.schema import VendorPeriodAgg


def make_agg(total: int, ontime: int, delay_counts: dict[str, int]) -> VendorPeriodAgg:
    return VendorPeriodAgg(
        vendor_id="V1",
        period="June",
        total_count=total,
        ontime_count=ontime,
        late_delay_reason_counts=Counter(delay_counts),
    )


class TestBuildDelayContext:
    def test_nodelay_dominant_basic(self):
        ctx = build_delay_context(make_agg(100, 0, {"NODELAY": 80, "TRAFFIC": 20}))
        assert ctx.total_late_count == 100
        assert ctx.nodelay_count == 80
        assert ctx.nodelay_share == pytest.approx(0.8)
        assert ctx.nodelay_dominates is True
        assert ctx.top_non_nodelay_reason == "TRAFFIC"
        assert ctx.top_non_nodelay_count == 20

    def test_nodelay_not_dominant_when_less_than_other(self):
        ctx = build_delay_context(make_agg(100, 0, {"NODELAY": 40, "TRAFFIC": 60}))
        assert ctx.nodelay_dominates is False

    def test_nodelay_not_dominant_on_tie(self):
        """Tie: NODELAY=50, TRAFFIC=50 — tie is NOT domination."""
        ctx = build_delay_context(make_agg(100, 0, {"NODELAY": 50, "TRAFFIC": 50}))
        assert ctx.nodelay_dominates is False

    def test_nodelay_not_dominant_when_zero(self):
        ctx = build_delay_context(make_agg(100, 0, {"TRAFFIC": 100}))
        assert ctx.nodelay_dominates is False

    def test_nodelay_dominant_when_only_reason(self):
        """NODELAY > 0 with no non-NODELAY reasons — vacuously dominates."""
        ctx = build_delay_context(make_agg(100, 50, {"NODELAY": 50}))
        assert ctx.nodelay_dominates is True
        assert ctx.top_non_nodelay_reason is None
        assert ctx.top_non_nodelay_count == 0
        assert ctx.top_non_nodelay_share == 0.0

    def test_tie_broken_by_lexicographic_order(self):
        """TRAFFIC and DRIVER both count=30; 'DRIVER' < 'TRAFFIC' → DRIVER wins."""
        ctx = build_delay_context(
            make_agg(100, 0, {"NODELAY": 10, "TRAFFIC": 30, "DRIVER": 30})
        )
        assert ctx.top_non_nodelay_reason == "DRIVER"
        assert ctx.top_non_nodelay_count == 30

    def test_no_late_trips(self):
        ctx = build_delay_context(make_agg(100, 100, {}))
        assert ctx.total_late_count == 0
        assert ctx.nodelay_share == 0.0
        assert ctx.nodelay_dominates is False
        assert ctx.top_non_nodelay_reason is None
        assert ctx.top_non_nodelay_count == 0

    def test_full_distribution_preserved(self):
        counts = {"NODELAY": 70, "TRAFFIC": 20, "DRIVER": 10}
        ctx = build_delay_context(make_agg(100, 0, counts))
        assert ctx.full_distribution == counts

    def test_nodelay_share_computed_from_total_late(self):
        # total=200, ontime=100, late=100, NODELAY=80
        ctx = build_delay_context(make_agg(200, 100, {"NODELAY": 80, "TRAFFIC": 20}))
        assert ctx.total_late_count == 100
        assert ctx.nodelay_share == pytest.approx(0.8)

    def test_top_non_nodelay_share_is_fraction_of_late(self):
        # late=100, NODELAY=70, TRAFFIC=30 → top_share = 30/100 = 0.3
        ctx = build_delay_context(make_agg(100, 0, {"NODELAY": 70, "TRAFFIC": 30}))
        assert ctx.top_non_nodelay_share == pytest.approx(0.3)

    def test_meera_pavlov_june_calibration(self):
        """Profile 6 calibration: NODELAY=1518, TRAFFIC=97, DRIVER=34, EMPLOYEE=17."""
        ctx = build_delay_context(
            make_agg(
                5294,
                3628,
                {"NODELAY": 1518, "TRAFFIC": 97, "DRIVER": 34, "EMPLOYEE": 17},
            )
        )
        assert ctx.total_late_count == 1666
        assert ctx.nodelay_count == 1518
        assert ctx.nodelay_dominates is True
        assert ctx.top_non_nodelay_reason == "TRAFFIC"
        assert ctx.top_non_nodelay_count == 97
