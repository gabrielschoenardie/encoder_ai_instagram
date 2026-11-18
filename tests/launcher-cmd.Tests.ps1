#Requires -Version 5.1
# L2F5: launcher.cmd nao deve propagar o PSModulePath herdado (pwsh 7) ao powershell.exe 5.1.

$canRun = ($env:OS -eq 'Windows_NT')

BeforeAll {
    $canRun = ($env:OS -eq 'Windows_NT')
    $script:repoRoot = Split-Path -Parent $PSScriptRoot

    function script:Invoke-TestProcess {
        param(
            [string]$FileName,
            [string]$Arguments,
            [string]$WorkingDirectory,
            [hashtable]$Env = @{},
            [string[]]$RemoveEnv = @()
        )
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $FileName
        $psi.Arguments = $Arguments
        $psi.WorkingDirectory = $WorkingDirectory
        $psi.UseShellExecute = $false
        $psi.RedirectStandardInput = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        foreach ($k in $RemoveEnv) { [void]$psi.EnvironmentVariables.Remove($k) }
        foreach ($k in $Env.Keys) { $psi.EnvironmentVariables[$k] = [string]$Env[$k] }
        $p = [System.Diagnostics.Process]::Start($psi)
        $p.StandardInput.Close()
        $so = $p.StandardOutput.ReadToEndAsync()
        $se = $p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit(90000)) { $p.Kill(); throw "timeout: $FileName $Arguments" }
        $p.WaitForExit()
        [pscustomobject]@{ ExitCode = $p.ExitCode; Stdout = $so.Result; Stderr = $se.Result }
    }

    function script:Read-Probe {
        param([string]$Path)
        $r = @{ Mods = @() }
        $inMods = $false
        foreach ($line in (Get-Content -LiteralPath $Path)) {
            if ($inMods) { $r.Mods += $line; continue }
            if ($line -eq 'MODS<<') { $inMods = $true; continue }
            $i = $line.IndexOf('=')
            $r[$line.Substring(0, $i)] = $line.Substring($i + 1)
        }
        $r
    }

    if ($canRun) {
        $script:folder = Join-Path ([System.IO.Path]::GetTempPath()) ('l2f5 test ' + [guid]::NewGuid().ToString('N'))
        $script:work = Join-Path ([System.IO.Path]::GetTempPath()) ('l2f5 work ' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $script:folder, $script:work | Out-Null
        Copy-Item -LiteralPath (Join-Path $script:repoRoot 'launcher.cmd') -Destination (Join-Path $script:folder 'launcher.cmd')

        $fake = @'
$out = $env:FAKE_OUT
$mods = Get-Module -ListAvailable | Sort-Object Name, Version, ModuleBase | ForEach-Object { '{0}|{1}|{2}' -f $_.Name, $_.Version, $_.ModuleBase }
$lines = @(
    ('ARGS=' + ($args -join '|')),
    ('CWD=' + (Get-Location).Path),
    ('PSM=' + $env:PSModulePath),
    ('FILEHASH=' + [bool](Get-Command Get-FileHash -EA SilentlyContinue)),
    ('EXPAND=' + [bool](Get-Command Expand-Archive -EA SilentlyContinue)),
    'MODS<<'
) + @($mods)
Set-Content -LiteralPath $out -Value $lines
exit [int]$env:FAKE_RC
'@
        Set-Content -LiteralPath (Join-Path $script:folder 'launcher.ps1') -Value $fake -Encoding ASCII

        $parts = @((Join-Path $script:folder 'custom-mods'))
        $pf = $env:ProgramFiles
        if (Test-Path -LiteralPath "$pf\PowerShell\7\Modules") { $parts += "$pf\PowerShell\7\Modules"; $parts += "$pf\PowerShell\Modules" }
        $parts += "$pf\WindowsPowerShell\Modules"
        $parts += "$env:SystemRoot\system32\WindowsPowerShell\v1.0\Modules"
        $script:inherited = ($parts -join ';')
        $script:defaults = @("$pf\WindowsPowerShell\Modules", "$env:SystemRoot\system32\WindowsPowerShell\v1.0\Modules")
        $script:cmdPath = Join-Path $script:folder 'launcher.cmd'

        function script:Invoke-Launcher {
            param([string]$Rc, [string]$ProbeName)
            $probe = Join-Path $script:folder $ProbeName
            $res = Invoke-TestProcess -FileName 'cmd.exe' -WorkingDirectory $script:work `
                -Arguments ('/d /s /c ""' + $script:cmdPath + '" -NoDownload "arg com espaco""') `
                -Env @{ PSModulePath = $script:inherited; FAKE_RC = $Rc; FAKE_OUT = $probe }
            [pscustomobject]@{ Result = $res; Probe = (Read-Probe $probe) }
        }

        $script:run0 = Invoke-Launcher -Rc '0' -ProbeName 'probe0.txt'
        $script:run7 = Invoke-Launcher -Rc '7' -ProbeName 'probe7.txt'

        $baseProbe = Join-Path $script:folder 'probe-base.txt'
        $null = Invoke-TestProcess -FileName 'powershell.exe' -WorkingDirectory $script:work `
            -Arguments ('-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $script:folder 'launcher.ps1') + '"') `
            -Env @{ FAKE_RC = '0'; FAKE_OUT = $baseProbe } -RemoveEnv @('PSModulePath')
        $script:baseline = Read-Probe $baseProbe

        $before = $env:PSModulePath
        $script:callerRes = Invoke-TestProcess -FileName 'cmd.exe' -WorkingDirectory $script:work `
            -Arguments ('/d /v:on /c "call "' + $script:cmdPath + '" -x & echo PSM=!PSModulePath!"') `
            -Env @{ PSModulePath = $script:inherited; FAKE_RC = '0'; FAKE_OUT = (Join-Path $script:folder 'probe-f.txt') }
        $script:testProcPsmUnchanged = ($env:PSModulePath -eq $before)
    }
}

AfterAll {
    foreach ($d in @($script:folder, $script:work)) {
        if ($d -and (Test-Path -LiteralPath $d)) { Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

Describe 'launcher.cmd e o PSModulePath herdado (L2F5)' {
    It 'o filho nao recebe entrada customizada nem \PowerShell\7\ e recebe as entradas padrao do 5.1' -Skip:(-not $canRun) {
        $entries = $script:run0.Probe['PSM'] -split ';' | Where-Object { $_ }
        ($entries | Where-Object { $_ -like '*custom-mods*' }) | Should -BeNullOrEmpty
        ($entries | Where-Object { $_ -like '*\PowerShell\7\*' }) | Should -BeNullOrEmpty
        foreach ($d in $script:defaults) { $entries | Should -Contain $d }
    }

    It 'Get-FileHash e Expand-Archive existem no filho' -Skip:(-not $canRun) {
        $script:run0.Probe['FILEHASH'] | Should -Be 'True'
        $script:run0.Probe['EXPAND'] | Should -Be 'True'
    }

    It 'a lista de modulos descobertos no filho e identica a do baseline sem PSModulePath' -Skip:(-not $canRun) {
        $script:baseline.Mods.Count | Should -BeGreaterThan 0
        ($script:run0.Probe.Mods -join "`n") | Should -BeExactly ($script:baseline.Mods -join "`n")
    }

    It 'argumentos chegam intactos e o diretorio de trabalho e a pasta do launcher' -Skip:(-not $canRun) {
        $script:run0.Probe['ARGS'] | Should -BeExactly '-NoDownload|arg com espaco'
        $script:run0.Probe['CWD'] | Should -BeExactly $script:folder
    }

    It 'propaga o codigo de saida 0' -Skip:(-not $canRun) {
        $script:run0.Result.ExitCode | Should -Be 0
    }

    It 'propaga o codigo de saida 7' -Skip:(-not $canRun) {
        $script:run7.Result.ExitCode | Should -Be 7
    }

    It 'o chamador mantem o PSModulePath herdado intacto depois do call' -Skip:(-not $canRun) {
        $line = ($script:callerRes.Stdout -split "`r?`n" | Where-Object { $_ -like 'PSM=*' } | Select-Object -Last 1)
        $line | Should -BeExactly ('PSM=' + $script:inherited)
        $script:testProcPsmUnchanged | Should -BeTrue
    }

    It 'launcher.cmd: setlocal antes de set PSModulePath= antes de powershell.exe' {
        $lines = Get-Content -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'launcher.cmd')
        $iSet = @(0..($lines.Count - 1) | Where-Object { $lines[$_] -match '^\s*setlocal\b' })
        $iClr = @(0..($lines.Count - 1) | Where-Object { $lines[$_] -match '^\s*set\s+"PSModulePath="\s*$' })
        $iPs = @(0..($lines.Count - 1) | Where-Object { $lines[$_] -match '^\s*powershell\.exe\b' })
        $iSet.Count | Should -BeGreaterThan 0
        $iClr.Count | Should -BeGreaterThan 0
        $iPs.Count | Should -BeGreaterThan 0
        $iSet[0] | Should -BeLessThan $iClr[0]
        $iClr[0] | Should -BeLessThan $iPs[0]
    }
}
