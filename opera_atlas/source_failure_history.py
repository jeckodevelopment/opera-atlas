"""Track consecutive observed technical failures, independent of publication."""
from datetime import datetime, timedelta

GRACE_HOURS = 24

def instant(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError):
        return None

def is_failure(row, *, field):
    state = row.get(field)
    if field == "status":
        return (state in ("unavailable_or_invalid", "partial_pagination")
                and row.get("diagnostic") != "future_official_programme_unverified")
    return state == "unavailable_or_invalid"

def with_history(row, old, *, checked_at, previous_checked_at=None, field="status"):
    """Never count elapsed wall time without a subsequent failed execution."""
    current = instant(checked_at)
    if current is None:
        raise ValueError("invalid source check timestamp")
    result = dict(row, last_attempt_at=checked_at)
    if not is_failure(row, field=field):
        return dict(result, first_failure_at=None, consecutive_failures=0)
    first, count = checked_at, 1
    previous = instant(old.get("last_attempt_at") or previous_checked_at)
    if is_failure(old, field=field) and previous is not None and previous <= current:
        # Migrate old snapshots using their last actually observed failed
        # attempt, never their last successful scan or an invented timestamp.
        old_first = instant(old.get("first_failure_at"))
        first = (old.get("first_failure_at") if old_first is not None
                 and old_first <= previous else old.get("last_attempt_at") or previous_checked_at)
        n = old.get("consecutive_failures")
        count = (n if type(n) is int and n >= 1 else 1) + int(current > previous)
    return dict(result, first_failure_at=first, consecutive_failures=count)

def outage(row, *, field="status"):
    """Return raw failure duration and escalation, based solely on observations."""
    first = instant(row.get("first_failure_at"))
    latest = instant(row.get("last_attempt_at"))
    count = row.get("consecutive_failures", 0)
    if not is_failure(row, field=field):
        return {"failure_state":"none", "failure_hours":None,
                "first_failure_at":None, "consecutive_failures":0,
                "requires_technical_attention":False}
    valid = first is not None and latest is not None and first <= latest
    persistent = (valid and type(count) is int and count >= 2
                  and latest-first >= timedelta(hours=GRACE_HOURS))
    return {"failure_state":"persistent" if persistent else "transient",
            "failure_hours":round((latest-first).total_seconds()/3600, 3) if valid else None,
            "first_failure_at":row.get("first_failure_at") if valid else None,
            "consecutive_failures":count if type(count) is int and count >= 0 else 0,
            "requires_technical_attention":bool(persistent)}
