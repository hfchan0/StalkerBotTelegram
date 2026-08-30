from archive_monitor.app import _is_rate_limited_error


def test_recognizes_instagram_rate_limit_errors() -> None:
    assert _is_rate_limited_error(RuntimeError("Instagram responded with HTTP error 429"))
    assert not _is_rate_limited_error(RuntimeError("Instagram session expired"))