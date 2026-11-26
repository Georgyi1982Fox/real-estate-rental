# Bina.ai: автообновление (TASK-125).
# Запускает планировщик Windows раз в 10 минут (включить — auto-update-on.bat).
# Есть новое в develop на GitHub — скачивает и пересобирает Docker, как update-bina.bat.
# Журнал — auto-update.log рядом с этим файлом.

Set-Location -LiteralPath $PSScriptRoot
$log = Join-Path $PSScriptRoot 'auto-update.log'

function Write-Log([string]$text) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $text" | Out-File -FilePath $log -Append -Encoding utf8
}

# Журнал не растёт бесконечно
if ((Test-Path $log) -and (Get-Item $log).Length -gt 1MB) {
    Move-Item -LiteralPath $log -Destination "$log.old" -Force
}

# Docker ещё не запущен (компьютер только включили) — проверим в следующий раз
docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Log 'Docker не запущен — пропускаю'; exit 0 }

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne 'develop') { Write-Log "Ветка $branch, а не develop — пропускаю"; exit 0 }

git fetch -q origin develop *> $null
if ($LASTEXITCODE -ne 0) { Write-Log 'Не удалось связаться с GitHub — пропускаю'; exit 0 }

$here = (git rev-parse HEAD).Trim()
$there = (git rev-parse origin/develop).Trim()
if ($here -eq $there) { Write-Log 'Обновлений нет'; exit 0 }

Write-Log "Обновляю: $($here.Substring(0, 7)) -> $($there.Substring(0, 7))"
$out = git pull --ff-only origin develop 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "Ошибка git pull: $($out -join ' ')"
    exit 1
}
# Тот же старт, что в update-bina.bat: пересобрать и перезапустить сервисы и сайт
$out = docker compose up -d --build 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "Ошибка docker compose: $(($out | Select-Object -Last 5) -join ' ')"
    exit 1
}
Write-Log 'Готово: приложение обновлено'
