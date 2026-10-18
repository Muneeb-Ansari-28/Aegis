$ErrorActionPreference = "Stop"

# PSScriptRoot is the repo root (where this script lives).
$repoRoot = $PSScriptRoot
$engineDir = Join-Path $repoRoot "engine"
$desktopDir = Join-Path $repoRoot "desktop"

# Prefer the .venv Python so the engine's dependencies are always available.
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        throw "Python was not found. Create a .venv or add Python 3.12+ to PATH."
    }
    Write-Warning ".venv not found -- falling back to system Python ($python)."
}

# Use npm.cmd (the batch wrapper) because npm.ps1 cannot be launched directly.
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) {
    $commonPaths = @(
        "C:\Program Files\nodejs\npm.cmd",
        "C:\Program Files (x86)\nodejs\npm.cmd"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) { $npm = $p; break }
    }
}
if (-not $npm) {
    throw "npm was not found on PATH. Install Node.js and try again."
}

if (-not (Test-Path (Join-Path $desktopDir "node_modules"))) {
    Write-Host "Installing desktop dependencies..."
    Push-Location $desktopDir
    try {
        & $npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    }
    finally { Pop-Location }
}

Push-Location $engineDir
try {
    & $python -c "import fastapi, uvicorn"
    if ($LASTEXITCODE -ne 0) {
        throw "Engine dependencies are missing. Run: $python -m pip install -r `"$engineDir\requirements.txt`""
    }
}
finally { Pop-Location }

# ---------------------------------------------------------------------------
# Helper: start a process and return a live System.Diagnostics.Process handle.
# Using this instead of Start-Process avoids the cmd-wrapper issue on Windows
# where the returned handle exits immediately after spawning the real child.
# ---------------------------------------------------------------------------
function Start-LiveProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName               = $FilePath
    $psi.Arguments              = $ArgumentList -join " "
    $psi.WorkingDirectory       = $WorkingDirectory
    $psi.UseShellExecute        = $false   # must be false to get a live handle
    $psi.CreateNoWindow         = $false   # show the console window

    $proc = [System.Diagnostics.Process]::Start($psi)
    return $proc
}

$engineProcess  = $null
$desktopProcess = $null

function Stop-ProcessTree {
    param([int]$ProcessId)
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) { Stop-ProcessTree -ProcessId $child.ProcessId }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) { Stop-Process -Id $ProcessId -Force }
}

try {
    Write-Host "Starting Aegis Engine..."
    $engineProcess = Start-LiveProcess `
        -FilePath        $python `
        -ArgumentList    @("main.py") `
        -WorkingDirectory $engineDir

    # Give the engine a moment to bind its port before starting the frontend.
    Start-Sleep -Seconds 3

    Write-Host "Starting Aegis Desktop..."
    $desktopProcess = Start-LiveProcess `
        -FilePath        $npm `
        -ArgumentList    @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $desktopDir

    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:3000/"

    Write-Host ""
    Write-Host "Aegis is running  -> http://127.0.0.1:3000/"
    Write-Host "Engine API        -> http://127.0.0.1:8765/"
    Write-Host "Press Ctrl+C to stop both processes."

    # Keep alive until one of the child processes exits unexpectedly.
    while (-not $engineProcess.HasExited -and -not $desktopProcess.HasExited) {
        Start-Sleep -Milliseconds 500
        $engineProcess.Refresh()
        $desktopProcess.Refresh()
    }

    if ($engineProcess.HasExited) {
        throw "The engine process exited unexpectedly with code $($engineProcess.ExitCode)."
    }
    throw "The desktop process exited unexpectedly with code $($desktopProcess.ExitCode)."
}
finally {
    Write-Host "`nShutting down Aegis..."
    if ($engineProcess  -and -not $engineProcess.HasExited)  { Stop-ProcessTree -ProcessId $engineProcess.Id  }
    if ($desktopProcess -and -not $desktopProcess.HasExited) { Stop-ProcessTree -ProcessId $desktopProcess.Id }
    Write-Host "Done."
}
