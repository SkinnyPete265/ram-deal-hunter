[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$taskName = "RAM Deal Hunter - Home Scanner"

if (-not (Test-Path (Join-Path $root ".git"))) {
    throw "Please CLONE the GitHub repository with GitHub Desktop or git. A downloaded ZIP cannot sync results to GitHub."
}

foreach ($program in @("git", "py")) {
    if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
        throw "Missing $program. Install Git for Windows (with Git Credential Manager) and Python 3.11+ before running setup."
    }
}

Write-Host ""
Write-Host "RAM Deal Hunter: Windows background scanner setup"
Write-Host "Repo: $root"
Write-Host ""
Write-Host "Installing Python dependencies..."
& py -3 -m pip install --disable-pip-version-check -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }

Write-Host ""
Write-Host "First scan and GitHub authentication check:"
Write-Host "If Git Credential Manager prompts you, sign into SkinnyPete265."
Write-Host "No token or GitHub password is stored by this project."
Write-Host ""
& (Join-Path $PSScriptRoot "Run-LocalScan.ps1")
if ($LASTEXITCODE -ne 0) { throw "Initial scan/publish failed; review logs\local-scanner.log." }
if (-not (Test-Path (Join-Path $root "docs\local-data.json"))) {
    throw "Initial scan snapshot not found. Please use RUN_LOCAL_SCAN.bat to diagnose the problem."
}

$scriptPath = Join-Path $PSScriptRoot "Run-LocalScan.ps1"
$powershellPath = Join-Path $PSHOME "powershell.exe"
$arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $scriptPath + '" -Unattended'

$action = New-ScheduledTaskAction -Execute $powershellPath -Argument $arguments -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddHours(8) -RepetitionInterval (New-TimeSpan -Hours 8) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 25) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Scan desktop DDR4 prices every 8 hours from this PC; publish public listing data to GitHub." -Force | Out-Null

Write-Host ""
Write-Host "SUCCESS: $taskName installed."
Write-Host "The first scan was uploaded; the next is scheduled in about 8 hours."
Write-Host "Task runs while this Windows user is signed in, even if the PC is locked."
Write-Host "You can inspect it in Windows Task Scheduler or read logs\local-scanner.log."
Write-Host "Public dashboard: https://skinnypete265.github.io/ram-deal-hunter/"
