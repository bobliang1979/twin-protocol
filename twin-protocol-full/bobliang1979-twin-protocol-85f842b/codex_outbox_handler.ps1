# codex_outbox_handler.ps1 — 处理来自 Hermes 的入站 tool_request
# 由 FileSystemWatcher 或外部 cron 触发
# 用法: .\codex_outbox_handler.ps1

$outboxPath = "$PSScriptRoot\codex_outbox.jsonl"
$processedFile = "$PSScriptRoot\.processed_ids.txt"

# Load processed IDs
$processed = @()
if (Test-Path $processedFile) {
    $processed = Get-Content $processedFile
}

# Read outbox, find unprocessed tool_requests from hermes
$lines = Get-Content $outboxPath
foreach ($line in $lines) {
    if (-not $line.Trim()) { continue }
    try {
        $req = $line | ConvertFrom-Json
        if ($req.type -ne "tool_request" -or $req.source -ne "hermes") { continue }
        if ($req.request_id -in $processed) { continue }

        $requestId = $req.request_id
        $tool = $req.tool
        $params = $req.params
        $result = $null
        $error = $null

        Write-Host "[Handler] Processing $tool ($requestId)..."

        switch ($tool) {
            "shell.run" {
                $cmd = $params.command
                $timeout = if ($params.timeout) { $params.timeout } else { 30 }
                try {
                    $output = & powershell -NoProfile -Command $cmd 2>&1
                    $result = @{
                        stdout = ($output | Out-String).Trim()
                        exit_code = $LASTEXITCODE
                    }
                } catch {
                    $error = $_.Exception.Message
                }
            }
            "js.eval" {
                $code = $params.code
                $timeout = if ($params.timeout) { $params.timeout } else { 30 }
                # Node.js eval — requires node.exe in PATH
                try {
                    $tmpFile = [System.IO.Path]::GetTempFileName() + ".js"
                    $code | Out-File -FilePath $tmpFile -Encoding utf8
                    $output = & node $tmpFile 2>&1
                    Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
                    $result = @{
                        stdout = ($output | Out-String).Trim()
                        exit_code = $LASTEXITCODE
                    }
                } catch {
                    $error = $_.Exception.Message
                    # Fallback to PowerShell eval
                    try {
                        $output = iex $code 2>&1
                        $result = @{
                            stdout = ($output | Out-String).Trim()
                            exit_code = 0
                            note = "executed via PowerShell fallback"
                        }
                    } catch {
                        $error = $_.Exception.Message
                    }
                }
            }
            "workspace.read" {
                $path = $params.path
                if (Test-Path $path) {
                    $content = Get-Content $path -Raw
                    $result = @{
                        content = $content
                        size = (Get-Item $path).Length
                        path = $path
                    }
                } else {
                    $error = "File not found: $path"
                }
            }
            default {
                $error = "Unknown tool: $tool"
            }
        }

        # Write result back to outbox
        $response = @{
            type = "tool_result"
            request_id = $requestId
            source = "codex"
            target = "hermes"
            tool = $tool
            result = $result
            error = $error
            _ts = (Get-Date -Format "o")
        }
        $response | ConvertTo-Json -Compress -Depth 5 | Out-File $outboxPath -Encoding utf8 -Append
        Write-Host "[Handler] $requestId done. error=$error"

        # Mark as processed
        $requestId | Out-File $processedFile -Encoding utf8 -Append
    } catch {
        Write-Host "[Handler] Parse error: $_"
    }
}
