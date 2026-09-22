#requires -Version 7.4
param(
    [Parameter(Mandatory = $true)]
    [string]$IsccPath
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
uv sync --locked --extra test --group dev
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $python -m pytest -q
& $python -m PyInstaller .\packaging\vscodl2.spec --clean --noconfirm
& $python .\scripts\smoke_frozen_browser.py .\dist\VSCODL2\VSCODL2-worker.exe
$version = & $python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])'
& $IsccPath "/DMyAppVersion=$version" .\packaging\installer.iss
Get-FileHash -Algorithm SHA256 -LiteralPath ".\dist\installer\VSCODL2-$version-Windows-x64-Setup.exe" |
    ForEach-Object { '{0}  {1}' -f $_.Hash.ToLowerInvariant(), (Split-Path -Leaf $_.Path) } |
    Set-Content -LiteralPath .\dist\installer\SHA256SUMS.txt -Encoding ascii
Write-Output "Release installer: $projectRoot\dist\installer\VSCODL2-$version-Windows-x64-Setup.exe"
