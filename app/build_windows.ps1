# Build "Twi OCR" for Windows: app\dist\Twi OCR\ (the app folder) and
# app\dist\Twi-OCR-Windows.zip (to share). Tesseract is packed inside, so
# people only need to unzip it and open "Twi OCR.exe".
#
# GitHub builds it with .github/workflows/build-windows.yml. To build on a
# Windows PC instead, from the project folder in PowerShell:
#     choco install tesseract            # or the UB Mannheim installer
#     pip install -r app\requirements-windows.txt
#     powershell -ExecutionPolicy Bypass -File app\build_windows.ps1
# The models must be in models\ (from the GitHub release), and the word list
# for the l -> i fix in data\ (python download.py) if you want it included.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$Root = (Get-Location).Path

foreach ($model in "twi", "twi_1879") {
    if (-not (Test-Path "models\$model.traineddata")) {
        throw "Missing models\$model.traineddata (download it from the GitHub release)."
    }
}

# Tesseract, copied without its own language files: the app brings its models.
$Tesseract = if ($env:TESSERACT_DIR) { $env:TESSERACT_DIR } else { Join-Path $env:ProgramFiles "Tesseract-OCR" }
if (-not (Test-Path (Join-Path $Tesseract "tesseract.exe"))) {
    throw "Tesseract not found in $Tesseract. Install it (choco install tesseract) or set TESSERACT_DIR."
}
$Vendor = "app\build\tesseract"
if (Test-Path $Vendor) { Remove-Item -Recurse -Force $Vendor }
New-Item -ItemType Directory -Force $Vendor | Out-Null
Get-ChildItem $Tesseract | Where-Object { $_.Name -ne "tessdata" -and $_.Name -notlike "uninstall*" } |
    Copy-Item -Destination $Vendor -Recurse
& "$Vendor\tesseract.exe" --version

$Extra = @()
if (Test-Path "data\twi_ghananlp.txt") {
    $Extra += @("--add-data", "$Root\data\twi_ghananlp.txt;data")
} else {
    Write-Warning "data\twi_ghananlp.txt not found, so the app's l -> i fix will be off."
}

pyinstaller --noconfirm --windowed --name "Twi OCR" `
    --distpath app\dist --workpath app\build\pyinstaller --specpath app\build `
    --paths "$Root" --hidden-import postcorrect --hidden-import orthography `
    --exclude-module pandas --exclude-module rapidfuzz --exclude-module numpy `
    --add-data "$Root\app\ui;ui" `
    --add-data "$Root\models\twi.traineddata;models" `
    --add-data "$Root\models\twi_1879.traineddata;models" `
    --add-data "$Root\orthography\christaller_1879.tsv;orthography" `
    --add-data "$Root\$Vendor;tesseract" `
    @Extra `
    app\twi_ocr_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

Copy-Item "$Root\THIRD_PARTY_NOTICES.md", "$Root\LICENSE" "app\dist\Twi OCR\"
$Zip = "app\dist\Twi-OCR-Windows.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path "app\dist\Twi OCR" -DestinationPath $Zip
Write-Host "Built: app\dist\Twi OCR\ and $Zip"
