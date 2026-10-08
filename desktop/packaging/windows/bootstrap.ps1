<#
.SYNOPSIS
    Post-install bootstrap for the LeRTX Windows installer.

    Ensures a real (non Microsoft Store stub) Python 3.11 or 3.12 interpreter
    is available, installing one silently from python.org if necessary, then
    runs the existing, tested `desktop/manage.py setup` and `install` flow
    from within the just-installed application directory.

    This script intentionally does not duplicate manage.py's own dependency
    logic - it only solves the one thing manage.py cannot: Windows has no
    reliable built-in way to get a real Python 3.11 onto PATH non-interactively.
#>
param(
    [Parameter(Mandatory = $true)][string]$InstallDir
)

$ErrorActionPreference = 'Stop'

function Find-RealPython311 {
    $candidates = New-Object System.Collections.Generic.List[string]

    try {
        $viaLauncher = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $viaLauncher) { $candidates.Add($viaLauncher.Trim()) }
    } catch {}

    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath -and $onPath.Source -notlike '*WindowsApps*') {
        # A python.exe under WindowsApps is the Microsoft Store app-execution-alias
        # stub, not a real interpreter; it fails under non-interactive sessions.
        $candidates.Add($onPath.Source)
    }

    $userInstall = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path $userInstall) { $candidates.Add($userInstall) }

    foreach ($candidate in $candidates) {
        try {
            $version = & $candidate -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and ($version.Trim() -eq '3.11' -or $version.Trim() -eq '3.12')) {
                return $candidate
            }
        } catch {}
    }
    return $null
}

$python = Find-RealPython311
if (-not $python) {
    Write-Output 'No usable Python 3.11/3.12 found; installing Python 3.11 for the current user...'
    $installer = Join-Path $env:TEMP 'lertx-python-3.11.9-amd64.exe'
    Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile $installer
    Start-Process -FilePath $installer -ArgumentList '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1', 'Include_test=0' -Wait
    Remove-Item $installer -ErrorAction SilentlyContinue
    $python = Find-RealPython311
    if (-not $python) {
        throw 'Python 3.11 installation completed but no usable interpreter was found afterward.'
    }
}

Write-Output "Using Python interpreter: $python"

$managePy = Join-Path $InstallDir 'desktop\manage.py'

& $python $managePy setup
if ($LASTEXITCODE -ne 0) { throw "LeRTX setup failed (exit code $LASTEXITCODE)." }

# The Start Menu shortcut is created natively by the installer's own [Icons]
# section, not by manage.py install - Inno Setup then owns its lifecycle
# (including clean removal on uninstall) without relying on this script or
# the app's own venv still existing at uninstall time.

Write-Output 'LeRTX setup complete.'
