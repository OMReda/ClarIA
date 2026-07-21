$projectDir = "C:\Users\r3d4\.gemini\antigravity-ide\scratch\plateforme-restitution"
$zipFile = "C:\Users\r3d4\.gemini\antigravity-ide\scratch\plateforme-restitution_safe.zip"

Write-Host "Packaging project for sharing..."

# We create a temporary staging folder to copy only the safe files
$tempDir = Join-Path $env:TEMP "plateforme-safe-pkg"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
New-Item -ItemType Directory -Path $tempDir | Out-Null

# List of folders/files to EXCLUDE
$excludeList = @(
    "node_modules",
    ".venv",
    ".git",
    "__pycache__",
    "storage",
    ".env",
    "dev.db",
    "plateforme.db"
)

# Copy everything EXCEPT the excluded items
Get-ChildItem -Path $projectDir -Recurse | Where-Object {
    $path = $_.FullName
    $shouldInclude = $true
    foreach ($ex in $excludeList) {
        if ($path -match "\\$ex\\?" -or $path -match "\\$ex$") {
            $shouldInclude = $false
            break
        }
    }
    return $shouldInclude
} | ForEach-Object {
    $targetPath = $_.FullName.Replace($projectDir, $tempDir)
    if ($_.PSIsContainer) {
        if (!(Test-Path $targetPath)) { New-Item -ItemType Directory -Path $targetPath | Out-Null }
    } else {
        $parent = Split-Path $targetPath
        if (!(Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
        Copy-Item -Path $_.FullName -Destination $targetPath
    }
}

# Create an empty storage folder just so the app doesn't crash on boot for the friend
New-Item -ItemType Directory -Path "$tempDir\storage" | Out-Null
New-Item -ItemType File -Path "$tempDir\storage\.gitkeep" | Out-Null

# Create the ZIP
if (Test-Path $zipFile) { Remove-Item -Force $zipFile }
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile

# Cleanup
Remove-Item -Recurse -Force $tempDir

Write-Host "Done! Safe ZIP created at: $zipFile"
