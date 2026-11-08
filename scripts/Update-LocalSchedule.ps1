# Update the task owned by the current Windows user to an 8-hour interval.
# This is idempotent and does not create a task if the scanner was never installed.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$taskName = "RAM Deal Hunter - Home Scanner"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "Home Scanner task not installed; nothing to migrate."
    return
}

$desired = [TimeSpan]::FromHours(8)
$alreadyConfigured = $false
foreach ($existingTrigger in @($task.Triggers)) {
    $repetition = $existingTrigger.Repetition
    if ($null -eq $repetition -or [string]::IsNullOrEmpty($repetition.Interval)) {
        continue
    }
    try {
        if ([System.Xml.XmlConvert]::ToTimeSpan($repetition.Interval) -eq $desired) {
            $alreadyConfigured = $true
            break
        }
    } catch {
        # Older task definitions can have unparseable interval values.
    }
}

if ($alreadyConfigured) {
    Write-Host "Home Scanner is already scheduled every 8 hours."
    return
}

# Schedule next run eight hours after this migration; keep existing action,
# security principal, login restrictions and task settings unchanged.
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddHours(8) -RepetitionInterval $desired -RepetitionDuration (New-TimeSpan -Days 3650)
Set-ScheduledTask -TaskName $taskName -Trigger $trigger -ErrorAction Stop | Out-Null
Write-Host "Updated Windows Home Scanner to run every 8 hours. Manual scans still work."
