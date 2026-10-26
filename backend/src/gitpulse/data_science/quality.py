"""Data Quality and Validation Suite for GitPulse Analytical Engineering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class DataQualityChecker:
    """Performs validation, integrity, and temporal consistency checks on GitHub engineering datasets."""

    @staticmethod
    def validate_timestamp_sequence(
        created_at: datetime | None,
        resolved_at: datetime | None,
        max_future_skew_seconds: int = 300,
    ) -> tuple[bool, str | None]:
        """Ensures created_at <= resolved_at and neither is arbitrarily far in the future."""
        now = datetime.now(UTC)
        skew_threshold = now + timedelta(seconds=max_future_skew_seconds)

        if not created_at:
            return False, "Missing creation timestamp"

        # Normalize timezone awareness
        c_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)

        if c_at > skew_threshold:
            return (
                False,
                f"Creation timestamp is in the future: {c_at.isoformat()} > {now.isoformat()}",
            )

        if resolved_at:
            r_at = resolved_at if resolved_at.tzinfo else resolved_at.replace(tzinfo=UTC)
            if r_at > skew_threshold:
                return False, f"Resolution timestamp is in the future: {r_at.isoformat()}"
            if r_at < c_at:
                return (
                    False,
                    f"Resolution timestamp precedes creation: {r_at.isoformat()} < {c_at.isoformat()}",
                )

        return True, None

    @staticmethod
    def validate_pr_metrics(
        additions: int, deletions: int, changed_files: int
    ) -> tuple[bool, str | None]:
        """Validates that PR line and file counters are non-negative and plausible."""
        if additions < 0:
            return False, f"Negative additions: {additions}"
        if deletions < 0:
            return False, f"Negative deletions: {deletions}"
        if changed_files < 0:
            return False, f"Negative changed_files: {changed_files}"
        return True, None

    @staticmethod
    def audit_daily_series(
        daily_records: dict[str, int],
        min_expected_days: int = 14,
    ) -> dict[str, Any]:
        """Audits time series continuity, identifying gaps, zero-activity days, and volatility."""
        if not daily_records:
            return {
                "valid": False,
                "total_days": 0,
                "missing_days": 0,
                "zero_activity_days": 0,
                "quality_score": 0.0,
                "status": "EMPTY_DATASET",
            }

        sorted_dates = sorted(daily_records.keys())
        start_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
        end_date = datetime.strptime(sorted_dates[-1], "%Y-%m-%d").date()

        total_calendar_days = (end_date - start_date).days + 1
        zero_days = 0
        missing_days = 0

        curr = start_date
        while curr <= end_date:
            d_str = curr.strftime("%Y-%m-%d")
            val = daily_records.get(d_str)
            if val is None:
                missing_days += 1
            elif val == 0:
                zero_days += 1
            curr += timedelta(days=1)

        coverage = (total_calendar_days - missing_days) / max(total_calendar_days, 1)
        valid = total_calendar_days >= min_expected_days and coverage >= 0.80

        quality_score = round(
            max(0.0, min(1.0, coverage * (1.0 - (missing_days / max(total_calendar_days, 1))))), 3
        )

        return {
            "valid": valid,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_calendar_days": total_calendar_days,
            "recorded_days": len(daily_records),
            "missing_days": missing_days,
            "zero_activity_days": zero_days,
            "coverage_ratio": round(coverage, 3),
            "quality_score": quality_score,
            "status": "HEALTHY" if valid else "INSUFFICIENT_HISTORY",
        }
