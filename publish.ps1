# ── AutoDeploy AI — Build & Publish to PyPI ──────────────────────────────────

Write-Host ""
Write-Host "  > Cleaning dist..." -ForegroundColor Cyan
Remove-Item -Path "dist\*" -Force -ErrorAction SilentlyContinue
Write-Host "  v  dist cleaned" -ForegroundColor Green

Write-Host ""
Write-Host "  > Building package..." -ForegroundColor Cyan
python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Host "  x  Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  v  Build success" -ForegroundColor Green

Write-Host ""
Write-Host "  > Uploading to PyPI..." -ForegroundColor Cyan
python -m twine upload dist/*
if ($LASTEXITCODE -ne 0) {
    Write-Host "  x  Upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  v  Published successfully!" -ForegroundColor Green
Write-Host ""
