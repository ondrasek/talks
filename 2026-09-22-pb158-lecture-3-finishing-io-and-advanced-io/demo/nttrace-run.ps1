# nttrace-run.ps1 - run NtTrace64 on a program, write the capture, and never hang.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File ..\nttrace-run.ps1 -Out CAPTURE.txt [-TimeoutSec 120] <NtTrace64 args...>
#   (no "--" separator: the PowerShell binder rejects it; the remaining arguments are the NtTrace64 command line)
#
# Over an SSH session with stdout redirected, NtTrace64 finishes tracing (the
# program's last line and "Thread ... exit code" are in the file) but does not
# exit - observed 2026-09-20 on iocost.exe. So: start it with the capture as its
# redirected stdout, wait up to TimeoutSec, then kill whatever is left. The
# capture is complete the moment the traced program has exited; the wait is
# only for a tidy exit.
# PositionalBinding=$false: without it PowerShell binds the first bare word
# (the program to trace) to -TimeoutSec and fails. Named switches only; every
# unnamed argument is the NtTrace64 command line.
[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$TimeoutSec = 120,
  [string]$NtTrace = "C:\Program Files\NtTrace64\NtTrace64.exe",
  [Parameter(ValueFromRemainingArguments=$true)][string[]]$Cmd
)
$quoted = $Cmd | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }
$p = Start-Process -FilePath $NtTrace -ArgumentList $quoted -RedirectStandardOutput $Out -NoNewWindow -PassThru
if (-not $p.WaitForExit($TimeoutSec * 1000)) {
  Write-Host "nttrace-run: NtTrace64 still attached after $TimeoutSec s; killing it (capture is complete if the program exited)"
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Get-Process -Name ($Cmd | Where-Object { $_ -like "*.exe" } | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) }) -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
$lines = (Get-Content $Out | Measure-Object -Line).Lines
Write-Host "nttrace-run: $Out - $lines line(s)"
