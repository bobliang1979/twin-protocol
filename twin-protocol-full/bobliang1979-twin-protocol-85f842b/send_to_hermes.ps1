param(
    [Parameter(Mandatory=$true)]
    [string]$Message,
    [string]$Type = "message",
    [string]$Target = "hermes",
    [string]$ReplyTo = ""
)

$payload = @{
    id = [guid]::NewGuid().ToString()
    type = $Type
    timestamp = (Get-Date -Format "o")
    source = "codex"
    target = $Target
    payload = @{
        text = $Message
    }
}

if ($ReplyTo) {
    $payload.payload.reply_to = $ReplyTo
}

$jsonLine = $payload | ConvertTo-Json -Compress
$jsonLine | Out-File -FilePath "$PSScriptRoot\codex_outbox.jsonl" -Encoding utf8 -Append

Write-Host "[Outbox] Sent to ${Target}: ${Message}"
