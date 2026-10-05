<# One command to prepare the pinned environment and run LeRTX on Windows. #>
[CmdletBinding()]
param([string]$Scene)

$ErrorActionPreference = 'Stop'
$manageScript = Join-Path $PSScriptRoot 'desktop\manage.py'
$manageArgs = @($manageScript, 'run')
if ($Scene) { $manageArgs += @('--scene', $Scene) }

# Prefer this checkout's interpreter after the first successful setup.
$candidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') {
    $candidates += $pythonCommand.Source
}
foreach ($version in @('3.11', '3.12')) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher -and $launcher.Source -notlike '*WindowsApps*') {
        try {
            $found = & $launcher.Source "-$version" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $found) { $candidates += $found.Trim() }
        } catch { }
    }
}
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try {
        & $candidate -c 'import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)' 2>$null
    } catch { continue }
    if ($LASTEXITCODE -eq 0) {
        & $candidate @manageArgs
        exit $LASTEXITCODE
    }
}
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    & $uvCommand.Source run --no-project --python 3.11 @manageArgs
    exit $LASTEXITCODE
}
throw 'Install Python 3.11/3.12 or uv, then run .\run.ps1 again. Microsoft Store Python aliases are not supported.'
