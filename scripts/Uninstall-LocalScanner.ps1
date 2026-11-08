$ErrorActionPreference = "Stop"
$taskName = "RAM Deal Hunter - Home Scanner"
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled scans. Source files and collected price history are unchanged."
} else {
    Write-Host "No RAM Deal Hunter scheduled task was found."
}
