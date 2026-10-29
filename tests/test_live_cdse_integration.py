"""
Dedicated Explicitly Invoked Integration Test for Authentic Live CDSE Downloads.

This test is skipped during standard automated unit test runs to protect against
unintended multi-gigabyte bandwidth consumption.

To execute explicitly:
    ALLOW_LIVE_CDSE_DOWNLOADS=1 pytest tests/test_live_cdse_integration.py -v
"""

import os
import pytest

try:
    from backend.app.raster_ingestion_service import CopernicusDataAccessManager
except ImportError:
    from app.raster_ingestion_service import CopernicusDataAccessManager


@pytest.mark.skipif(
    os.environ.get("ALLOW_LIVE_CDSE_DOWNLOADS", "0").lower() not in ("1", "true", "yes"),
    reason="Live CDSE downloads are skipped by default. Run with ALLOW_LIVE_CDSE_DOWNLOADS=1 to test live downloads."
)
def test_live_cdse_authenticated_access():
    """Verifies live CDSE authentication and connectivity when explicitly invoked."""
    mgr = CopernicusDataAccessManager()
    if not mgr.has_credentials():
        pytest.skip("CDSE credentials (CDSE_USERNAME and CDSE_PASSWORD or CDSE_ACCESS_TOKEN) not configured in environment.")

    auth_status = mgr.verify_authentication(timeout_sec=15.0)
    assert auth_status["configured"] is True
    assert auth_status["authenticated"] is True
    assert auth_status["status"] == "AUTHENTICATED_OK"
