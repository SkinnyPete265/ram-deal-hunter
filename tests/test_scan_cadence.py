"""Keep the cloud, installer and migration cadence aligned."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_schedule_is_eight_hours_and_manual_dispatch_kept():
    workflow = (ROOT / ".github/workflows/scan.yml").read_text(encoding="utf-8")
    assert "cron: '17 2,10,18 * * *'" in workflow
    assert "workflow_dispatch:" in workflow
    assert "17,47 * * * *" not in workflow


def test_new_windows_install_and_existing_task_migration_are_eight_hours():
    installer = (ROOT / "scripts/Install-LocalScanner.ps1").read_text(encoding="utf-8")
    migration = (ROOT / "scripts/Update-LocalSchedule.ps1").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/Run-LocalScan.ps1").read_text(encoding="utf-8")
    assert "RepetitionInterval (New-TimeSpan -Hours 8)" in installer
    assert "[TimeSpan]::FromHours(8)" in migration
    assert "Set-ScheduledTask" in migration
    assert 'Update-LocalSchedule.ps1' in runner
    assert 'RUN_LOCAL_SCAN.bat' in (ROOT / "README.md").read_text(encoding="utf-8")


def test_dashboard_tolerates_scheduled_scan_delays_without_permanent_freshness():
    merge = (ROOT / "docs/merge.js").read_text(encoding="utf-8")
    assert "MAX_AGE_MS = 12 * 60 * 60 * 1000" in merge
