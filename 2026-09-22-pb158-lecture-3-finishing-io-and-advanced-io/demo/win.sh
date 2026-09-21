#!/usr/bin/env bash
# win.sh — build, run and trace the Windows demos from macOS over SSH.
#
#   ./win.sh setup                    one master SSH connection (YubiKey PIN once), the MSVC env wrapper, the remote folder
#   ./win.sh sync                     copy the demo folders to the Windows machine
#   ./win.sh build  [folder]          nmake /f Makefile.msvc all   (x64 tool-chain via vcvars64)
#   ./win.sh run    [folder]          the folder's `run` target
#   ./win.sh trace  [folder]          the folder's `trace` target (NtTrace64), then fetch the captures
#   ./win.sh trace-py [folder]        the PyWin32 variants under NtTrace64, then fetch
#   ./win.sh fetch  [folder]          copy NtTrace64-*.txt captures back and count them
#   ./win.sh sh 'command'             run any cmd.exe line inside the MSVC environment
#   ./win.sh all                      setup, sync, build, run, trace, trace-py, fetch — everything
#
# folder = durability | waiting | destinations-win32 | iodemo-c   (default: all three Windows-demo folders)
#
# Env: WIN_HOST (default administrator@10.211.55.3)   WIN_DIR (default C:/Users/administrator/pb158/demo)
#      VCVARS   (default "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat")
#      NTTRACE  (default "C:\Program Files\NtTrace64\NtTrace64.exe")   PYTHON_WIN (default: the Program Files Python)
#
# The master connection lives at /tmp/claude/sshwin for an hour, so the YubiKey
# PIN is asked once. Windows-side paths use forward slashes for scp and
# backslashes for cmd; both forms are derived from WIN_DIR here.
set -euo pipefail
cd "$(dirname "$0")"
WIN_HOST="${WIN_HOST:-administrator@10.211.55.3}"
WIN_DIR="${WIN_DIR:-C:/Users/administrator/pb158/demo}"
WIN_DIR_BS="${WIN_DIR//\//\\}"
VCVARS="${VCVARS:-C:\\Program Files\\Microsoft Visual Studio\\18\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat}"
NTTRACE="${NTTRACE:-C:\\Program Files\\NtTrace64\\NtTrace64.exe}"
PYTHON_WIN="${PYTHON_WIN:-C:\\Program Files\\Python314\\python.exe}"
CTL=/tmp/claude/sshwin
SSH=(ssh -o ControlMaster=auto -o ControlPath="$CTL" -o ControlPersist=60m "$WIN_HOST")
SCP=(scp -q -o ControlPath="$CTL")
FOLDERS=(durability waiting destinations-win32)
ENVCMD="${WIN_DIR_BS}\\..\\pb158-env.cmd"

folders() { if [ $# -gt 0 ]; then echo "$@"; else echo "${FOLDERS[@]}"; fi; }
win()     { "${SSH[@]}" "$@"; }                       # one cmd.exe line
winenv()  { win "$ENVCMD $*"; }                       # inside the MSVC x64 environment
nmake()   { local f=$1; shift; winenv "cd ${WIN_DIR_BS}\\$f && nmake /nologo /f Makefile.msvc PYTHON=\"$PYTHON_WIN\" NTTRACE=\"$NTTRACE\" $*"; }

cmd_setup() {
  mkdir -p /tmp/claude
  printf '@echo off\r\ncall "%s" >nul\r\n%%*\r\n' "$VCVARS" > /tmp/claude/pb158-env.cmd
  win "mkdir ${WIN_DIR_BS} 2>nul & echo connected to %COMPUTERNAME% as %USERNAME%"
  "${SCP[@]}" /tmp/claude/pb158-env.cmd "$WIN_HOST:${WIN_DIR}/../pb158-env.cmd"
  winenv "cl 2>&1 | findstr /i version"
  win "\"$PYTHON_WIN\" -c \"import sys, win32file, win32pdh, win32pipe; print('python', sys.version.split()[0], 'pywin32 ok')\"" \
    || echo "python or pywin32 missing: set PYTHON_WIN, or on the VM run: \"$PYTHON_WIN\" -m pip install pywin32"
}
cmd_sync()  { "${SCP[@]}" -r $(folders "$@") nttrace-count.py "$WIN_HOST:${WIN_DIR}/"; echo "synced: $(folders "$@")"; }
cmd_build() { for f in $(folders "$@"); do echo "== build $f"; nmake "$f" all; done; }
cmd_run()   { for f in $(folders "$@"); do echo "== run $f"; nmake "$f" run; done; }
cmd_trace() { for f in $(folders "$@"); do echo "== trace $f"; nmake "$f" trace; done; cmd_fetch "$@"; }
cmd_trace_py() { for f in $(folders "$@"); do echo "== trace-py $f"; nmake "$f" trace-py; done; cmd_fetch "$@"; }
cmd_fetch() {
  for f in $(folders "$@"); do
    "${SCP[@]}" "$WIN_HOST:${WIN_DIR}/$f/NtTrace64-*.txt" "$f/" 2>/dev/null || echo "   (no captures in $f yet)"
  done
  ls */NtTrace64-*.txt 2>/dev/null | xargs -r python3 nttrace-count.py | grep -E '^==|^ +[0-9]+ ' | head -60
}
case "${1:-help}" in
  setup) cmd_setup ;;
  sync)  shift; cmd_sync "$@" ;;
  build) shift; cmd_build "$@" ;;
  run)   shift; cmd_run "$@" ;;
  trace) shift; cmd_trace "$@" ;;
  trace-py) shift; cmd_trace_py "$@" ;;
  fetch) shift; cmd_fetch "$@" ;;
  sh)    shift; winenv "$*" ;;
  all)   cmd_setup; cmd_sync; cmd_build; cmd_run; cmd_trace; cmd_trace_py ;;
  *)     sed -n '2,20p' "$0" ;;
esac
