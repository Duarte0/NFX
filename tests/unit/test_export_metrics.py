from nfx.exports.metrics import ExportMetrics


def test_export_metrics_keep_bounded_outcomes_only() -> None:
    metrics = ExportMetrics()
    metrics.record("request")
    metrics.record("compose", "available")
    metrics.record("compose", "partial")
    metrics.record("compose", "failed")
    metrics.record("download")
    metrics.record("denied")
    metrics.record("unknown", "fiscal-content")
    assert metrics.snapshot().requests == 1
    assert metrics.snapshot().available == 1
    assert metrics.snapshot().partial == 1
    assert metrics.snapshot().failed == 1
    assert metrics.snapshot().downloads == 1
    assert metrics.snapshot().denied_downloads == 1
