<#
.SYNOPSIS
    TVI Enterprise Network - Windows Environment Setup Script
.DESCRIPTION
    Sets up Python virtual environment (.venv), installs netmiko & pyyaml,
    verifies network automation dependencies, and checks VMnet network connectivity.
#>

[CmdletBinding()]
param(
    [switch]$SkipNetworkCheck
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  TVI Enterprise Network - Environment Setup (Windows)    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Detect Python
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    # Check if python 3.10 is available via launcher
    $hasPy310 = py --list 2>&1 | Select-String "3.10"
    if ($hasPy310) {
        $pythonCmd = "py -3.10"
        Write-Host "[+] Found Python 3.10 via 'py' launcher (Recommended for Netmiko)." -ForegroundColor Green
    } else {
        $pythonCmd = "py"
        Write-Host "[+] Using default 'py' launcher." -ForegroundColor Yellow
    }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
    Write-Host "[+] Using 'python' from PATH." -ForegroundColor Green
} else {
    Write-Error "[!] Neither 'py' nor 'python' was found. Please install Python 3.10+ from python.org."
    exit 1
}

# 2. Create virtual environment
$repoRoot = $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"

if (-not (Test-Path $venvPath)) {
    Write-Host "[*] Creating virtual environment at '$venvPath'..." -ForegroundColor Cyan
    Invoke-Expression "$pythonCmd -m venv `"$venvPath`""
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[!] Failed to create virtual environment."
        exit 1
    }
    Write-Host "[+] Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "[+] Virtual environment already exists at '$venvPath'." -ForegroundColor Green
}

# 3. Locate venv python and pip
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "[!] Could not locate python.exe inside virtual environment ($venvPython)."
    exit 1
}

# 4. Install dependencies
Write-Host "[*] Installing/Verifying requirements from requirements.txt..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPip install -r (Join-Path $repoRoot "requirements.txt")

if ($LASTEXITCODE -ne 0) {
    Write-Error "[!] Failed to install dependencies."
    exit 1
}
Write-Host "[+] All Python dependencies installed successfully." -ForegroundColor Green

# 5. Dependency verification
Write-Host "[*] Verifying netmiko and pyyaml imports..." -ForegroundColor Cyan
$verifyScript = "import netmiko; import yaml; import paramiko; print(f'Netmiko version: {netmiko.__version__}'); print(f'PyYAML version: {yaml.__version__}')"
& $venvPython -c $verifyScript

if ($LASTEXITCODE -ne 0) {
    Write-Error "[!] Import verification failed."
    exit 1
}
Write-Host "[+] Import verification passed." -ForegroundColor Green

# 6. Optional Host Network / VMnet Check
if (-not $SkipNetworkCheck) {
    Write-Host "`n[*] Checking VMware Management Network (192.168.1.0/24)..." -ForegroundColor Cyan
    $adapters = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like "192.168.1.*" }
    if ($adapters) {
        Write-Host "[+] Host adapter found on 192.168.1.x: $($adapters.IPAddress) ($($adapters.InterfaceAlias))" -ForegroundColor Green
    } else {
        Write-Host "[!] Notice: No host adapter found with IP 192.168.1.x." -ForegroundColor Yellow
        Write-Host "    To enable direct laptop-to-lab SSH without a Linux node in EVE:" -ForegroundColor Yellow
        Write-Host "    Run 'EVE_Lab\scripts\setup_vmware_vmnet.ps1' as Administrator." -ForegroundColor Yellow
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Setup completed! To activate the environment run:" -ForegroundColor Green
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  To run automation:" -ForegroundColor Green
Write-Host "    python Automation\auto_provision.py" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
