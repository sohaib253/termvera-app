<#
Builds the Termvera desktop installer:
  build\desktop\installer\Termvera-Setup-<version>.exe

One installer containing everything the app needs: Python runtime and
libraries, the web interface, Tesseract OCR, and the local database engine
(SQLite, built into Python). The target machine needs nothing installed.

Build-machine prerequisites (developer laptop only):
  - apps\api\.venv with requirements.txt + requirements-dev.txt installed
    (the dev requirements include PyInstaller and pefile)
  - Node.js (for the web build)
  - Tesseract installed (the build copies the parts it needs)
  - Inno Setup 6 (winget install JRSoftware.InnoSetup)

Usage (from anywhere):
  powershell -ExecutionPolicy Bypass -File apps\desktop\build.ps1 [-Version 0.2.0]
#>
param(
    [string]$Version = "0.1.0",
    [string]$TesseractDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\..\.."
$Desktop = "$Root\apps\desktop"
$Build = "$Root\build\desktop"
$Python = "$Root\apps\api\.venv\Scripts\python.exe"

function Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Find-First($paths) { $paths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1 }

New-Item -ItemType Directory -Force $Build | Out-Null

Step "Building the web interface (static export)"
Push-Location "$Root\apps\web"
try {
    if (-not (Test-Path node_modules)) { npm ci; if ($LASTEXITCODE) { throw "npm ci failed" } }
    # The desktop app serves the interface and the API from the same local
    # address, so API calls are relative. It must be the word "same-origin":
    # an empty value isn't inlined by Next.js and the dev default leaks in.
    $env:NEXT_PUBLIC_API_BASE_URL = "same-origin"
    Remove-Item -Recurse -Force out, .next -ErrorAction SilentlyContinue
    npx next build
    if ($LASTEXITCODE) { throw "Web build failed" }
} finally {
    Remove-Item Env:NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}

Step "Collecting Tesseract OCR"
if (-not $TesseractDir) {
    $TesseractDir = Find-First @(
        "$env:LOCALAPPDATA\Programs\Tesseract-OCR",
        "$env:ProgramFiles\Tesseract-OCR",
        "${env:ProgramFiles(x86)}\Tesseract-OCR"
    )
}
if (-not $TesseractDir -or -not (Test-Path "$TesseractDir\tesseract.exe")) {
    throw "Tesseract not found. Install it or pass -TesseractDir."
}
& $Python "$Desktop\collect_tesseract.py" $TesseractDir "$Build\tesseract"
if ($LASTEXITCODE) { throw "Collecting Tesseract failed" }

Step "Preparing icon and version info"
& $Python "$Desktop\make_icon.py" "$Desktop\termvera.ico" "$Root\apps\web\app\favicon.ico"
if ($LASTEXITCODE) { throw "Icon generation failed" }
$parts = ($Version.Split(".") + @("0", "0", "0"))[0..3] -join ", "
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($parts), prodvers=($parts)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('ProductName', 'Termvera'),
      StringStruct('FileDescription', 'Termvera'),
      StringStruct('FileVersion', '$Version'),
      StringStruct('ProductVersion', '$Version'),
      StringStruct('OriginalFilename', 'Termvera.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -Encoding utf8 "$Build\version_info.txt"

Step "Bundling the application (PyInstaller)"
& $Python -m PyInstaller --noconfirm --clean `
    --distpath "$Build\dist" --workpath "$Build\work" "$Desktop\termvera.spec"
if ($LASTEXITCODE) { throw "PyInstaller failed" }

Step "Creating the installer (Inno Setup)"
$Iscc = Find-First @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
if (-not $Iscc) { throw "Inno Setup 6 not found (winget install JRSoftware.InnoSetup)." }
& $Iscc /Q "/DAppVersion=$Version" "/DSourceDir=$Build\dist\Termvera" "/DOutputDir=$Build\installer" "$Desktop\installer.iss"
if ($LASTEXITCODE) { throw "Inno Setup failed" }

$installer = Get-Item "$Build\installer\Termvera-Setup-$Version.exe"
Step ("Done: {0} ({1:N0} MB)" -f $installer.FullName, ($installer.Length / 1MB))
