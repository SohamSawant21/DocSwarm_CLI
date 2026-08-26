$ErrorActionPreference = "Stop"

$Version = "v0.2.0"
$InstallDir = Join-Path $env:LOCALAPPDATA "DocSwarm"
$ExePath = Join-Path $InstallDir "docswarm.exe"

$DownloadUrl = "https://github.com/SohamSawant21/DocSwarm_CLI/releases/download/$Version/docswarm.exe"

Write-Host "Installing DocSwarm CLI $Version..."
Write-Host ""

# Create installation directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

# Download executable
Write-Host "Downloading DocSwarm CLI..."
Invoke-WebRequest `
    -Uri $DownloadUrl `
    -OutFile $ExePath

if (-not (Test-Path $ExePath)) {
    throw "Download failed. docswarm.exe was not found."
}

Write-Host "Downloaded to: $ExePath"

# Add installation directory to user's PATH
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")

$PathEntries = @()
if ($UserPath) {
    $PathEntries = $UserPath -split ";" | Where-Object { $_ -ne "" }
}

if ($PathEntries -notcontains $InstallDir) {
    $NewUserPath = if ($UserPath) {
        "$UserPath;$InstallDir"
    } else {
        $InstallDir
    }

    [Environment]::SetEnvironmentVariable(
        "Path",
        $NewUserPath,
        "User"
    )

    Write-Host "Added DocSwarm to the user PATH."
}
else {
    Write-Host "DocSwarm is already present in the user PATH."
}

# Verify executable
Write-Host ""
Write-Host "Verifying installation..."

& $ExePath --help

if ($LASTEXITCODE -ne 0) {
    throw "DocSwarm executable failed the verification step."
}

Write-Host ""
Write-Host "DocSwarm CLI installed successfully."
Write-Host ""
Write-Host "Installation directory:"
Write-Host $InstallDir
Write-Host ""
Write-Host "Open a NEW PowerShell window and run:"
Write-Host "    docswarm --help"