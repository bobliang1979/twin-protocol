# codex_outbox_watcher.ps1 — 实时监控 outbox，收到 Hermes tool_request 自动处理
# 后台运行：Start-Process powershell -ArgumentList "-NoProfile -File `"$PSScriptRoot\codex_outbox_watcher.ps1`"" -WindowStyle Hidden
# 或：PowerShell -NoProfile -File "C:\Users\10074\Documents\控制\codex_outbox_watcher.ps1"

$outboxPath = "C:\Users\10074\Documents\控制\codex_outbox.jsonl"
$handlerPath = "C:\Users\10074\Documents\控制\codex_outbox_handler.ps1"
$watcher = New-Object IO.FileSystemWatcher
$watcher.Path = [IO.Path]::GetDirectoryName($outboxPath)
$watcher.Filter = [IO.Path]::GetFileName($outboxPath)
$watcher.NotifyFilter = [IO.NotifyFilters]'LastWrite'
$watcher.EnableRaisingEvents = $true
$lastEvent = 0

Write-Host "[Watcher] Monitoring $outboxPath ... (Ctrl+C to stop)"

while ($true) {
    $result = $watcher.WaitForChanged([IO.WaitForChangedOptions]'Changed', 10000)
    if ($result.TimedOut) { continue }
    $now = [DateTime]::UtcNow.Ticks
    if ($now - $lastEvent -lt 5000000) { continue }  # debounce 500ms
    $lastEvent = $now
    Start-Sleep -Milliseconds 500  # let write finish
    & $handlerPath
}
