<#
.SYNOPSIS
    Wrapper para chamar pelo Agendador de Tarefas do Windows (ou manualmente).
    Sobe o servidor Django em segundo plano se ele ainda não estiver rodando,
    espera ficar pronto e então roda o bot de envio de relatórios.

.PARAMETER Frequencia
    DIARIA, SEMANAL ou MENSAL — processa só as inscrições dessa frequência.

.EXAMPLE
    powershell.exe -ExecutionPolicy Bypass -File automacoes\executar_envio.ps1 -Frequencia DIARIA

.NOTES
    MAILTRAP_API_TOKEN precisa estar definido como variável de ambiente
    PERMANENTE do usuário/sistema (via `setx`), não só na sessão do terminal —
    caso contrário o Agendador de Tarefas não vai enxergar o token.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("DIARIA", "SEMANAL", "MENSAL")]
    [string]$Frequencia
)

$ErrorActionPreference = "Stop"

$RaizProjeto = Split-Path -Parent $PSScriptRoot
$Python      = Join-Path $RaizProjeto "venv\Scripts\python.exe"
$Bot         = Join-Path $PSScriptRoot "bot_envio_relatorios.py"

if (-not $env:MAILTRAP_API_TOKEN) {
    throw "MAILTRAP_API_TOKEN nao definido. Rode 'setx MAILTRAP_API_TOKEN `"seu_token`"' uma vez e reabra a sessao."
}

# Sobe o servidor Django em segundo plano, se ainda não estiver respondendo.
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "Servidor Django ja esta rodando."
}
catch {
    Write-Host "Servidor Django nao esta rodando. Iniciando em segundo plano..."
    Start-Process -FilePath $Python `
        -ArgumentList "manage.py", "runserver", "127.0.0.1:8000" `
        -WorkingDirectory $RaizProjeto `
        -WindowStyle Hidden

    $pronto = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 2 | Out-Null
            $pronto = $true
            break
        }
        catch { }
    }
    if (-not $pronto) {
        throw "Servidor Django nao respondeu apos 30s."
    }
    Write-Host "Servidor Django pronto."
}

& $Python $Bot --frequencia $Frequencia
exit $LASTEXITCODE
