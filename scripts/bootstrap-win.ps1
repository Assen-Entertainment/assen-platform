#Requires -Version 5.1
<#
.SYNOPSIS
    Windows dev bootstrap for the Assen Platform backend + web (pure Windows
    toolchain, no WSL — ADR-10). Creates/repairs server\.venv-win, applies
    migrations, seeds demo data, and installs web\ dependencies.

.DESCRIPTION
    The POSIX scripts under scripts/ (build-local.sh, up-local.sh) assume a
    Linux/WSL host with docker compose driving the backend. This host is pure
    Windows with a checked-out venv (server\.venv-win) instead — this script
    is that path's equivalent bootstrap.

    Steps:
      1. Resolve the uv executable. uv is frequently missing from PATH in
         non-interactive Windows shells even when installed — a known trap on
         this host (see scripts/doctor-win.ps1).
      2. UV_PROJECT_ENVIRONMENT=.venv-win uv sync --frozen (create or repair
         server\.venv-win). If this fails with a file-in-use error, a running
         python/daphne process is holding a lock on server\.venv-win\Scripts\
         *.pyd — run scripts/doctor-win.ps1 first.
      3. server\.venv-win\Scripts\python.exe manage.py migrate --noinput
      4. server\.venv-win\Scripts\python.exe manage.py seed_demo
      5. npm ci --legacy-peer-deps (web\)

    Every step after uv sync invokes server\.venv-win\Scripts\python.exe
    directly (not `uv run`) — same non-interactive PATH trap as step 1 makes
    `uv run` unreliable here even once uv itself is resolved.

.PARAMETER SkipWeb
    Skip the web\ npm ci step.

.PARAMETER SkipSeed
    Skip manage.py seed_demo (migrate still runs).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\bootstrap-win.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipWeb,
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ServerDir  = Join-Path $RepoRoot "server"
$WebDir     = Join-Path $RepoRoot "web"
$VenvDir    = Join-Path $ServerDir ".venv-win"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$ManagePy   = Join-Path $ServerDir "manage.py"

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "bootstrap-win: $Message"
}

function Invoke-Checked {
    # Runs a native command and exits the script on a nonzero exit code — the
    # PS 5.1 equivalent of `set -e` for external processes, which do not raise
    # a terminating error on their own even with $ErrorActionPreference=Stop.
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$OnFailureHint
    )
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        Write-Host "error: '$FilePath $($ArgumentList -join ' ')' exited with code $LASTEXITCODE" -ForegroundColor Red
        if ($OnFailureHint) {
            Write-Host $OnFailureHint -ForegroundColor Yellow
        }
        exit $LASTEXITCODE
    }
}

function Resolve-UvExe {
    if ($env:UV_EXE -and (Test-Path $env:UV_EXE)) {
        return $env:UV_EXE
    }
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\uv\uv.exe")
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    Write-Host ""
    Write-Host "error: uv executable not found on PATH or in common install locations." -ForegroundColor Red
    Write-Host "  uv is often missing from PATH in non-interactive Windows shells even" -ForegroundColor Yellow
    Write-Host "  when installed - a known trap on this host." -ForegroundColor Yellow
    Write-Host '  Install:  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"' -ForegroundColor Yellow
    Write-Host "  Then open a new shell, or set UV_EXE to uv.exe's absolute path and re-run." -ForegroundColor Yellow
    exit 1
}

Write-Step "repo root: $RepoRoot"

$UvExe = Resolve-UvExe
Write-Step "using uv: $UvExe"

# --- server\.venv-win: create or repair -------------------------------------
Write-Step "server\.venv-win: UV_PROJECT_ENVIRONMENT=.venv-win uv sync --frozen"
$env:UV_PROJECT_ENVIRONMENT = ".venv-win"
try {
    & $UvExe --directory $ServerDir sync --frozen
    $syncExitCode = $LASTEXITCODE
}
finally {
    Remove-Item Env:\UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
}
if ($syncExitCode -ne 0) {
    Write-Host ""
    Write-Host "error: uv sync failed (exit $syncExitCode)." -ForegroundColor Red
    Write-Host "  A common cause on Windows: a running python/daphne process still has" -ForegroundColor Yellow
    Write-Host "  server\.venv-win\Scripts\*.pyd locked, so uv cannot replace it." -ForegroundColor Yellow
    Write-Host "  Diagnose:  powershell -ExecutionPolicy Bypass -File scripts\doctor-win.ps1" -ForegroundColor Yellow
    exit $syncExitCode
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "error: uv sync reported success but $VenvPython is missing." -ForegroundColor Red
    exit 1
}

# --- migrate + seed -----------------------------------------------------------
Write-Step "django migrate --noinput"
Invoke-Checked -FilePath $VenvPython -ArgumentList @($ManagePy, "migrate", "--noinput") `
    -OnFailureHint "Check DATABASE_URL (server\.env, default postgres://assen:assen@localhost:5432/assen) - is Postgres reachable (docker compose / Docker Desktop)?"

if (-not $SkipSeed) {
    Write-Step "django seed_demo"
    Invoke-Checked -FilePath $VenvPython -ArgumentList @($ManagePy, "seed_demo")
}
else {
    Write-Step "skipping seed_demo (-SkipSeed)"
}

# --- web\ -----------------------------------------------------------------
if (-not $SkipWeb) {
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npmCmd) {
        Write-Host "error: npm not found on PATH." -ForegroundColor Red
        exit 1
    }
    Write-Step "web: npm ci --legacy-peer-deps"
    Push-Location $WebDir
    try {
        Invoke-Checked -FilePath $npmCmd.Source -ArgumentList @("ci", "--legacy-peer-deps")
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Step "skipping web\ npm ci (-SkipWeb)"
}

# --- guidance ---------------------------------------------------------------
Write-Host ""
Write-Host "bootstrap-win: done." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  API (dev):        server\.venv-win\Scripts\python.exe server\manage.py runserver 127.0.0.1:8000"
Write-Host "  Web (dev):        cd web; npm run dev"
Write-Host "  Verify (server):  server\.venv-win\Scripts\ruff.exe check server ; server\.venv-win\Scripts\mypy.exe server ; server\.venv-win\Scripts\pytest.exe server"
Write-Host "  Lock/PATH issues: powershell -ExecutionPolicy Bypass -File scripts\doctor-win.ps1"
