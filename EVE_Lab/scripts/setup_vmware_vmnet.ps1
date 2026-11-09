<#
.SYNOPSIS
    Configures host VMnet1 network adapter and static route for TVI Lab Management.
.DESCRIPTION
    Must be executed as Administrator on Windows.
    1. Sets VMnet1 IP to 192.168.1.100 / 255.255.255.0.
    2. Adds persistent route to 192.168.0.0/22 via HQ Gateway 192.168.1.1.
#>

# Require Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "This script requires Administrator privileges to modify network adapters and route tables."
    Write-Warning "Please right-click PowerShell -> 'Run as Administrator', then re-run this script."
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  TVI EVE-NG Lab - Host VMnet Management Network Setup    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate VMnet1 adapter
$alias = (Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*VMware Virtual Ethernet Adapter for VMnet1*" -or $_.Name -like "*VMnet1*" }).Name

if (-not $alias) {
    Write-Error "VMnet1 network adapter not found. Please ensure VMware Workstation is installed and VMnet1 exists in Virtual Network Editor."
    exit 1
}

Write-Host "[+] Found VMnet1 adapter: $alias" -ForegroundColor Green

# 2. Assign static IP 192.168.1.100/24
$currentIP = (Get-NetIPAddress -InterfaceAlias $alias -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
if ($currentIP -eq "192.168.1.100") {
    Write-Host "[+] $alias already configured with 192.168.1.100/24." -ForegroundColor Green
} else {
    Write-Host "[*] Assigning IP 192.168.1.100/24 to $alias..." -ForegroundColor Cyan
    Remove-NetIPAddress -InterfaceAlias $alias -Confirm:$false -ErrorAction SilentlyContinue
    New-NetIPAddress -InterfaceAlias $alias -IPAddress 192.168.1.100 -PrefixLength 24 -ErrorAction Stop | Out-Null
    Write-Host "[+] IP configured successfully." -ForegroundColor Green
}

# 3. Add static route for TVI Multi-Site Management scope: 192.168.0.0/22 via HQ HSRP 192.168.1.1
$routeExists = Get-NetRoute -DestinationPrefix "192.168.0.0/22" -ErrorAction SilentlyContinue
if ($routeExists) {
    Write-Host "[+] Route 192.168.0.0/22 via 192.168.1.1 already exists." -ForegroundColor Green
} else {
    Write-Host "[*] Adding static route 192.168.0.0/22 via 192.168.1.1 on $alias..." -ForegroundColor Cyan
    New-NetRoute -DestinationPrefix "192.168.0.0/22" -InterfaceAlias $alias -NextHop "192.168.1.1" -PolicyStore Persistent -ErrorAction Stop | Out-Null
    Write-Host "[+] Route added successfully." -ForegroundColor Green
}

Write-Host "`nSetup completed. You can now SSH directly to TVI lab devices:" -ForegroundColor Green
Write-Host "  ssh admin@192.168.1.10   (HCMC Core Switch)"
Write-Host "  ssh admin@192.168.2.10   (Hanoi Switch)"
Write-Host "  ssh admin@192.168.3.10   (Da Nang Switch)"
