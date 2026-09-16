from __future__ import annotations

from dataclasses import dataclass

from moveinsync_ota.data.schema import VendorPeriodAgg


@dataclass
class DelayReasonContext:
    total_late_count: int
    nodelay_count: int
    nodelay_share: float
    nodelay_dominates: bool
    top_non_nodelay_reason: str | None
    top_non_nodelay_count: int
    top_non_nodelay_share: float
    full_distribution: dict[str, int]


def build_delay_context(agg: VendorPeriodAgg) -> DelayReasonContext:
    total_late = agg.total_count - agg.ontime_count
    full_dist: dict[str, int] = dict(agg.late_delay_reason_counts)
    nodelay_count = full_dist.get("NODELAY", 0)
    nodelay_share = nodelay_count / total_late if total_late > 0 else 0.0

    non_nodelay: dict[str, int] = {r: c for r, c in full_dist.items() if r != "NODELAY"}

    # Strict domination: NODELAY > 0 AND NODELAY > every individual non-NODELAY count.
    # A tie is NOT domination.
    if nodelay_count > 0 and (
        not non_nodelay or nodelay_count > max(non_nodelay.values())
    ):
        nodelay_dominates = True
    else:
        nodelay_dominates = False

    # Top non-NODELAY: highest count, ties broken lexicographically smallest reason.
    if non_nodelay:
        max_count = max(non_nodelay.values())
        tied = [r for r, c in non_nodelay.items() if c == max_count]
        top_reason: str | None = min(tied)
        top_count = max_count
        top_share = top_count / total_late if total_late > 0 else 0.0
    else:
        top_reason = None
        top_count = 0
        top_share = 0.0

    return DelayReasonContext(
        total_late_count=total_late,
        nodelay_count=nodelay_count,
        nodelay_share=nodelay_share,
        nodelay_dominates=nodelay_dominates,
        top_non_nodelay_reason=top_reason,
        top_non_nodelay_count=top_count,
        top_non_nodelay_share=top_share,
        full_distribution=full_dist,
    )
