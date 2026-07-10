#Requires -Version 5.1
<#
.SYNOPSIS
    Diagnose the Windows ".venv-win lock" trap: a running python\daphne
    process still has server\.venv-win\Scripts\*.pyd open, so `uv sync` fails
    with a file-in-use error.

.DESCRIPTION
    1. Lists every running process whose executable path is inside
       server\.venv-win - these are the only processes that CAN hold a lock
       on its files (a python.exe running from a different interpreter cannot
       lock this venv's DLLs).
    2. Lists whatever is listening on :8000 (the dev API port) and cross-
       references it against #1, since `manage.py runserver` / `daphne` left
       running in another terminal is the usual culprit.
    3. Prints safe-stop guidance (Stop-Process) - nothing is killed unless
       -KillLockers is passed explicitly.
    4. Always prints the additive-only uv workaround: `uv pip install
       --python server\.venv-win\Scripts\python.exe <package>` can add a NEW
       package without touching files a running process has locked, but it
       cannot repair/rebuild an already-locked file - a real
       `uv sync --frozen` still needs the locking process stopped first.

.PARAMETER KillLockers
    Stop every detected .venv-win-locking process (Stop-Process -Force). Off
    by default - this script is diagnostic-first.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\doctor-win.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\doctor-win.ps1 -KillLockers
#>

[CmdletBinding()]
param(
    [switch]$KillLockers
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir  = Join-Path $RepoRoot "server\.venv-win"

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "doctor-win: $Message"
}

Write-Step "repo root: $RepoRoot"
Write-Step "checking: $VenvDir"

if (-not (Test-Path $VenvDir)) {
    Write-Host "doctor-win: server\.venv-win does not exist yet - nothing to lock." -ForegroundColor Yellow
    Write-Host "  Run:  powershell -ExecutionPolicy Bypass -File scripts\bootstrap-win.ps1" -ForegroundColor Yellow
    exit 0
}

$VenvDirNorm = (Resolve-Path $VenvDir).Path.TrimEnd('\') + '\'

# --- 1) processes running FROM .venv-win (the only ones that can lock its files) ---
$venvProcs = @()
Get-Process | ForEach-Object {
    $path = $null
    try { $path = $_.Path } catch { $path = $null }
    if ($path -and $path.StartsWith($VenvDirNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
        $venvProcs += [PSCustomObject]@{
            ProcId = $_.Id
            Name   = $_.ProcessName
            Path   = $path
        }
    }
}
$venvPids = @()
if ($venvProcs.Count -gt 0) {
    $venvPids = $venvProcs | ForEach-Object { $_.ProcId }
}

# --- 2) :8000 listeners (usual culprit: manage.py runserver / daphne) -----------
$listenerPids = @()
try {
    $conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction Stop
    if ($conns) {
        $listenerPids = @($conns | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique)
    }
}
catch {
    # Get-NetTCPConnection (NetTCPIP module) may be unavailable - fall back to netstat.
    $lines = netstat -ano | Select-String ":8000\s+.*LISTENING"
    foreach ($line in $lines) {
        $fields = ($line.ToString() -split '\s+') | Where-Object { $_ -ne "" }
        $procId = $fields[-1]
        if ($procId -match '^\d+$') {
            $listenerPids += [int]$procId
        }
    }
    $listenerPids = @($listenerPids | Sort-Object -Unique)
}

if ($venvProcs.Count -eq 0) {
    Write-Host "doctor-win: no running process is executing from .venv-win - no lock detected." -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "doctor-win: FOUND $($venvProcs.Count) process(es) running from .venv-win (these can lock uv sync):" -ForegroundColor Red
    foreach ($p in $venvProcs) {
        $onPort8000 = ""
        if ($listenerPids -contains $p.ProcId) {
            $onPort8000 = " [listening on :8000]"
        }
        Write-Host ("  PID {0,-7} {1,-12} {2}{3}" -f $p.ProcId, $p.Name, $p.Path, $onPort8000)
    }
}

if ($listenerPids.Count -gt 0) {
    $unmatched = @($listenerPids | Where-Object { $venvPids -notcontains $_ })
    if ($unmatched.Count -gt 0) {
        Write-Host ""
        Write-Host "doctor-win: :8000 is also held by PID(s) not running from .venv-win: $($unmatched -join ', ')" -ForegroundColor Yellow
        Write-Host "  (not a .venv-win lock risk by itself, but it will block manage.py runserver/daphne from binding.)" -ForegroundColor Yellow
    }
}

if ($venvProcs.Count -gt 0) {
    Write-Host ""
    if ($KillLockers) {
        Write-Host "doctor-win: -KillLockers passed - stopping the process(es) above." -ForegroundColor Yellow
        foreach ($p in $venvProcs) {
            try {
                Stop-Process -Id $p.ProcId -Force -ErrorAction Stop
                Write-Host "  stopped PID $($p.ProcId)"
            }
            catch {
                Write-Host "  error: could not stop PID $($p.ProcId): $_" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "doctor-win: safe stop guidance (nothing was killed - pass -KillLockers to do this automatically):" -ForegroundColor Yellow
        foreach ($p in $venvProcs) {
            Write-Host "  Stop-Process -Id $($p.ProcId)   # $($p.Name)"
        }
        Write-Host "  Then re-run:  powershell -ExecutionPolicy Bypass -File scripts\bootstrap-win.ps1"
    }
}

Write-Host ""
Write-Host "doctor-win: additive-only workaround - if you only need to ADD a package" -ForegroundColor Cyan
Write-Host "  without stopping the locking process, this installs into .venv-win's" -ForegroundColor Cyan
Write-Host "  site-packages without touching files a running process already locked:" -ForegroundColor Cyan
Write-Host "    uv pip install --python server\.venv-win\Scripts\python.exe <package>" -ForegroundColor Cyan
Write-Host "  This does NOT repair or rebuild an already-locked file - it only adds" -ForegroundColor Cyan
Write-Host "  new ones. A real 'uv sync --frozen' still needs the locker stopped first." -ForegroundColor Cyan
