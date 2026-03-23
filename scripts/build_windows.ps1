$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $repoRoot 'dist'
$buildDir = Join-Path $repoRoot 'build'

if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

New-Item -ItemType Directory -Path $distDir | Out-Null

Write-Host 'Building Go executable...'
go build -o (Join-Path $distDir 'Go.exe') $repoRoot

Write-Host 'Building Python executable...'
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run pyinstaller --noconfirm --onefile --name python_service --distpath $distDir --workpath $buildDir --specpath $buildDir (Join-Path $repoRoot 'python_service/app.py')
} else {
    pyinstaller --noconfirm --onefile --name python_service --distpath $distDir --workpath $buildDir --specpath $buildDir (Join-Path $repoRoot 'python_service/app.py')
}

Write-Host 'Copying config and models...'
$config = Get-Content (Join-Path $repoRoot 'config.json') -Raw | ConvertFrom-Json
$config.models_dir = 'models'
$configPath = Join-Path $distDir 'config.json'
[System.IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))

$modelsSrc = Join-Path $repoRoot 'project/assets'
$modelsDst = Join-Path $distDir 'models'
Copy-Item $modelsSrc $modelsDst -Recurse -Force

Write-Host "Build complete: $distDir"
