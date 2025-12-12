from ytdl_bot.logic import quota_allows, quota_remaining


def test_quota_enforced_for_non_admin() -> None:
    assert quota_allows(used_bytes=400, limit_bytes=500, required_bytes=150, is_admin=False) is False


def test_quota_allows_admin_unlimited() -> None:
    assert quota_allows(used_bytes=10_000, limit_bytes=500, required_bytes=9_999_999, is_admin=True) is True


def test_quota_remaining_never_negative() -> None:
    assert quota_remaining(used_bytes=700, limit_bytes=500) == 0
    assert quota_remaining(used_bytes=100, limit_bytes=500) == 400