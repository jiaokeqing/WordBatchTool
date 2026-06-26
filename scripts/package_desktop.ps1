param(
    [ValidateSet("windows", "huawei-windows", "huawei-uos-arm64")]
    [string]$Target = "windows",
    [string]$PythonCommand = ""
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"
$Backend = Join-Path $Root "backend"
$Release = Join-Path $Root "release"
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$CargoBin = Join-Path $env:USERPROFILE ".cargo\bin"

if (Test-Path $CargoBin) {
    $env:PATH = "$CargoBin;$env:PATH"
}

function Require-Command {
    param(
        [string]$Name,
        [string[]]$VersionArgs,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $Name. $InstallHint"
    }

    try {
        & $Name @VersionArgs | Out-Null
    } catch {
        throw "Command is not usable: $Name. $InstallHint"
    }
}

function Test-CommandUsable {
    param(
        [string]$Name,
        [string[]]$VersionArgs
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        return $false
    }

    try {
        & $Name @VersionArgs | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Resolve-PythonCommand {
    param([string]$PreferredCommand)

    if ($PreferredCommand -and (Test-CommandUsable $PreferredCommand @("--version"))) {
        return @{ Command = $PreferredCommand; PrefixArgs = @() }
    }

    $Candidates = @("python", "python3", "py")
    foreach ($Candidate in $Candidates) {
        if ($Candidate -eq "py") {
            if (Test-CommandUsable $Candidate @("-3.12", "--version")) {
                return @{ Command = $Candidate; PrefixArgs = @("-3.12") }
            }
            if (Test-CommandUsable $Candidate @("-3", "--version")) {
                return @{ Command = $Candidate; PrefixArgs = @("-3") }
            }
        } elseif (Test-CommandUsable $Candidate @("--version")) {
            return @{ Command = $Candidate; PrefixArgs = @() }
        }
    }

    throw "No usable Python found. Install Python 3.12 and disable the Windows Store python.exe app execution alias, or pass -PythonCommand with the full python.exe path."
}

function Invoke-Python {
    param(
        [hashtable]$Python,
        [string[]]$Arguments
    )

    & $Python.Command @($Python.PrefixArgs) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Native {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

function Resolve-TargetTriple {
    param([string]$BuildTarget)

    switch ($BuildTarget) {
        "windows" { return "x86_64-pc-windows-msvc" }
        "huawei-windows" { return "x86_64-pc-windows-msvc" }
        "huawei-uos-arm64" { return "aarch64-unknown-linux-gnu" }
    }
}

function Assert-TargetHost {
    param([string]$BuildTarget)

    if ($BuildTarget -eq "huawei-uos-arm64") {
        throw "Huawei UOS ARM64 package must be built on a Tongxin UOS / Linux ARM64 target machine. This PowerShell script is only for Windows hosts."
    }
}

function Resolve-ReleaseDir {
    param([string]$BuildTarget)

    switch ($BuildTarget) {
        "windows" { return Join-Path $Release "windows-x64" }
        "huawei-windows" { return Join-Path $Release "huawei-windows-x64" }
        default { return Join-Path $Release $BuildTarget }
    }
}

$TargetTriple = Resolve-TargetTriple $Target
Assert-TargetHost $Target
$ResolvedPython = Resolve-PythonCommand $PythonCommand

Write-Host "Target platform: $Target"
Write-Host "Target triple: $TargetTriple"
Write-Host "Python command: $($ResolvedPython.Command) $($ResolvedPython.PrefixArgs -join ' ')"

Require-Command "pnpm.cmd" @("--version") "Install pnpm."
Require-Command "rustc" @("--version") "Install rustup / Rust stable-msvc."
Require-Command "cargo" @("--version") "Install rustup / Cargo."

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating project virtual environment..."
    Invoke-Python $ResolvedPython @("-m", "venv", ".venv")
}

Write-Host "Installing backend dependencies..."
Push-Location $Backend
Invoke-Native $VenvPython @("-m", "pip", "install", "--disable-pip-version-check", "--prefer-binary", "--timeout", "120", "--retries", "5", "-r", "requirements-sidecar.txt")
Pop-Location

Write-Host "Installing frontend dependencies..."
Push-Location $Frontend
Invoke-Native "pnpm.cmd" @("install", "--frozen-lockfile", "--store-dir", "..\.npm-cache\pnpm-store")
Pop-Location

Write-Host "Building Python sidecar..."
Push-Location $Root
Invoke-Native $VenvPython @("scripts\build_sidecar.py", "--target-triple", $TargetTriple)
Pop-Location

Write-Host "Building Tauri desktop package..."
Push-Location $Frontend
Invoke-Native "pnpm.cmd" @("tauri:build")
Pop-Location

Write-Host "Collecting release artifacts..."
$ReleaseDir = Resolve-ReleaseDir $Target
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Copy-Item -Force (Join-Path $Frontend "src-tauri\target\release\word-batch-workbench.exe") (Join-Path $ReleaseDir "格式通.exe")
Copy-Item -Force (Join-Path $Frontend "src-tauri\target\release\word-batch-sidecar.exe") (Join-Path $ReleaseDir "word-batch-sidecar.exe")
$NsisDir = Join-Path $Frontend "src-tauri\target\release\bundle\nsis"
if (Test-Path $NsisDir) {
    Get-ChildItem -Path $NsisDir -Filter "*setup.exe" | ForEach-Object {
        Copy-Item -Force $_.FullName (Join-Path $ReleaseDir $_.Name)
    }
}

Write-Host "Done. Check packages under frontend\src-tauri\target\release\bundle."
