param(
    [string]$FrontendPath = "frontend/Support-dashboard",
    [string]$StaticPath = "static"
)

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js/npm не установлены. Установите Node.js (https://nodejs.org) и повторите."
    exit 1
}

Push-Location $FrontendPath
try {
    if (Test-Path package-lock.json) {
        npm ci
    } else {
        npm install
    }
    npm run build
} finally {
    Pop-Location
}

# Копируем сборку Vite (dist) в static/
$dist = Join-Path $FrontendPath "dist"
if (-not (Test-Path $dist)) {
    Write-Error "Папка сборки не найдена: $dist. Проверьте, что сборка прошла успешно."
    exit 1
}

# Очищаем static и копируем новую сборку
if (Test-Path $StaticPath) {
    Remove-Item -Recurse -Force "$StaticPath/*" -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path $StaticPath | Out-Null
}

Copy-Item -Recurse -Force "$dist/*" $StaticPath

Write-Host "Frontend собран и скопирован в '$StaticPath'"
