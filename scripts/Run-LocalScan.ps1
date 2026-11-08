[CmdletBinding()]
param(
    [switch]$Unattended
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mutex = New-Object System.Threading.Mutex($false, "Local\RAMDealHunterScheduledScan")
$ownsLock = $false
$transcriptStarted = $false

try {
    try { $ownsLock = $mutex.WaitOne(0) }
    catch [System.Threading.AbandonedMutexException] { $ownsLock = $true }

    if (-not $ownsLock) {
        Write-Host "Another RAM Deal Hunter scan is running. Skipping this interval."
        return
    }

    $logDirectory = Join-Path $root "logs"
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $logFile = Join-Path $logDirectory "local-scanner.log"
    if ((Test-Path $logFile) -and (Get-Item $logFile).Length -gt 5MB) {
        Move-Item -Force $logFile (Join-Path $logDirectory "local-scanner.previous.log")
    }
    Start-Transcript -Path $logFile -Append | Out-Null
    $transcriptStarted = $true

    if (-not (Test-Path (Join-Path $root ".git"))) {
        throw "This must run from a Git clone, not a downloaded ZIP. Clone SkinnyPete265/ram-deal-hunter with GitHub Desktop."
    }

    $remote = & git -C $root remote get-url origin
    if ($LASTEXITCODE -ne 0) { throw "Could not read Git remote." }
    $remote = ($remote | Select-Object -First 1).Trim()
    if ($remote -notmatch '^(?:https://github\.com/|git@github\.com:)(?i:SkinnyPete265/ram-deal-hunter)(?:\.git)?/?$') {
        throw "Unexpected Git remote ($remote). Refusing to push anywhere else."
    }

    $branch = & git -C $root branch --show-current
    if ($LASTEXITCODE -ne 0 -or $branch -ne "main") {
        throw "Please check out the main branch before using the background scanner."
    }

    if ($Unattended) {
        # Scheduled tasks cannot answer interactive credential prompts.
        # Authentication must be set up by running RUN_LOCAL_SCAN.bat once.
        $env:GIT_TERMINAL_PROMPT = "0"
        $env:GCM_INTERACTIVE = "never"
    }

    Write-Host "[$(Get-Date -Format o)] Fetching latest RAM Deal Hunter version..."
    & git -C $root fetch origin main
    if ($LASTEXITCODE -ne 0) { throw "Git fetch failed. Check internet and Git authentication." }
    & git -C $root merge --ff-only origin/main
    if ($LASTEXITCODE -ne 0) {
        throw "Local Git checkout cannot fast-forward. Resolve local changes before running automated scans."
    }

    $env:RAM_DEAL_DATA_FILE = Join-Path $root "docs\local-data.json"
    $env:PYTHONDONTWRITEBYTECODE = "1"

    Write-Host "Running RAM scan from this Windows PC..."
    & py -3 (Join-Path $root "monitor.py")
    if ($LASTEXITCODE -ne 0) { throw "RAM scanner exited with status $LASTEXITCODE." }
    if (-not (Test-Path $env:RAM_DEAL_DATA_FILE)) { throw "Scanner did not produce a local snapshot." }

    & git -C $root add -- docs/local-data.json
    if ($LASTEXITCODE -ne 0) { throw "Could not stage local scan snapshot." }
    & git -C $root diff --cached --quiet -- docs/local-data.json

    if ($LASTEXITCODE -eq 0) {
        Write-Host "No local snapshot changes to publish."
        return
    }
    if ($LASTEXITCODE -ne 1) { throw "Could not check staged local data." }

    # Commit ONLY the scanner snapshot, not any other files staged by the user.
    & git -C $root -c "user.name=RAM Deal Hunter" -c "user.email=ram-deal-hunter@users.noreply.github.com" commit -m "chore: refresh Windows RAM scan" -- docs/local-data.json
    if ($LASTEXITCODE -ne 0) { throw "Could not commit local RAM snapshot." }

    $pushed = $false
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        & git -C $root push origin main
        if ($LASTEXITCODE -eq 0) {
            $pushed = $true
            break
        }

        Write-Host "Main changed during the scan. Re-syncing before retry $attempt..."
        & git -C $root fetch origin main
        if ($LASTEXITCODE -ne 0) { throw "Git fetch failed during retry." }
        & git -C $root rebase origin/main
        if ($LASTEXITCODE -ne 0) {
            & git -C $root rebase --abort | Out-Null
            throw "Automatic rebase failed. Local changes have been preserved; review Git status."
        }
    }

    if (-not $pushed) { throw "Could not publish snapshot after four push attempts." }
    Write-Host "[$(Get-Date -Format o)] Windows scan uploaded. GitHub Pages deployment should follow."
}
finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
    if ($ownsLock) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
