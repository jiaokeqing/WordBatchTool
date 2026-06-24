$ErrorActionPreference = "Stop"

Write-Host "Building frontend..."
Push-Location frontend
npm install
npm run build
Pop-Location

Write-Host "Installing backend dependencies..."
Push-Location backend
python -m pip install -r requirements.txt

Write-Host "Building Windows executable..."
pyinstaller WordBatchTool.spec --clean --noconfirm
Pop-Location

Write-Host "Done. EXE path: backend\dist\WordBatchTool.exe"
