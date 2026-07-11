# enable-dev-mode.ps1
# Enables Windows Developer Mode so file symlinks work without admin.
# Called automatically by setup.py on Windows.
# Must run elevated (setup.py handles the UAC prompt).

$RegPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
$KeyName  = "AllowDevelopmentWithoutDevLicense"

try {
    Set-ItemProperty -Path $RegPath -Name $KeyName -Value 1 -Type DWord -Force
    Write-Host "OK Developer Mode enabled"
    exit 0
} catch {
    Write-Host "FAIL $_"
    exit 1
}
