/* wait_peek.c — a hundred pipes nobody writes to, asked in turn. POLLING, on Windows, in C.
 *
 *   wait_peek.exe [PIPES=100] [SECS=2]
 *
 * WHAT THIS SHOWS
 *   The Windows twin of wait_blocking.py. Nothing ever arrives on any pipe, and
 *   the program still spends the whole two seconds asking: PeekNamedPipe on
 *   pipe 1, pipe 2, ... pipe 100, and again, and again. Every ask is a trip
 *   into the kernel that learns nothing. Compare wait_iocp.c, which asks once.
 *
 * WHAT TO LOOK AT
 *   1. The number of PeekNamedPipe calls in two seconds — hundreds of thousands
 *      untraced. That number is a RATE: twenty seconds would be ten times more,
 *      all for zero bytes.
 *   2. The "kernel counted" line: the kernel's own accounting of this process
 *      (GetProcessIoCounters, the counter Lecture 2 used) shows the same number
 *      as OTHER operations — every peek is a device-control style request.
 *   3. Under NtTrace64 (nmake trace) each PeekNamedPipe turns out to be THREE
 *      native calls: NtCreateEvent, NtFsControlFile(FSCTL_PIPE_PEEK), NtClose.
 *      Count under the tracer, time without it: the tracer slows the loop a
 *      hundredfold, so traced and untraced counts must not be compared.
 *
 * WHY IT MATTERS
 *   This is how a program waits when it does not know how to wait: it asks.
 *   The cost is paid precisely while nothing is happening — Kegel's C10K point.
 *
 * Build: nmake /f Makefile.msvc     (x64 Developer Command Prompt; NtTrace64 traces x64 binaries)
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

/* The kernel's per-process I/O accounting, printed as a difference. */
static void io_delta(const char *what, const IO_COUNTERS *before) {
    IO_COUNTERS now; GetProcessIoCounters(GetCurrentProcess(), &now);
    printf("%s: kernel counted READ ops +%llu, OTHER ops +%llu\n", what,
           (unsigned long long)(now.ReadOperationCount  - before->ReadOperationCount),
           (unsigned long long)(now.OtherOperationCount - before->OtherOperationCount));
}

int main(int argc, char **argv) {
    int pipes = argc > 1 ? atoi(argv[1]) : 100;
    double secs = argc > 2 ? atof(argv[2]) : 2.0;
    HANDLE *srv = calloc(pipes, sizeof(HANDLE)), *cli = calloc(pipes, sizeof(HANDLE));
    char name[64];

    /* A hundred named pipes, each with a CONNECTED client that never writes.
     * (PeekNamedPipe on an unconnected pipe would fail, not wait.) */
    for (int i = 0; i < pipes; i++) {
        snprintf(name, sizeof name, "\\\\.\\pipe\\pb158-peek-c-%d", i);
        srv[i] = CreateNamedPipeA(name, PIPE_ACCESS_INBOUND, PIPE_TYPE_BYTE | PIPE_WAIT, 1, 4096, 4096, 0, NULL);
        cli[i] = CreateFileA(name, GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
        if (srv[i] == INVALID_HANDLE_VALUE || cli[i] == INVALID_HANDLE_VALUE) { fprintf(stderr, "pipe %d failed: %lu\n", i, GetLastError()); return 1; }
        ConnectNamedPipe(srv[i], NULL);   /* the client is already there; returns at once (STATUS_PIPE_CONNECTED) */
    }

    IO_COUNTERS io0; GetProcessIoCounters(GetCurrentProcess(), &io0);
    LARGE_INTEGER f, t0, t; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t0);
    unsigned long long peeks = 0;

    /* THE LOOP THE LECTURE IS ABOUT: ask every pipe, round after round. */
    for (;;) {
        QueryPerformanceCounter(&t);
        if ((double)(t.QuadPart - t0.QuadPart) / (double)f.QuadPart >= secs) break;
        for (int i = 0; i < pipes; i++) {
            DWORD avail = 0;
            if (!PeekNamedPipe(srv[i], NULL, 0, NULL, &avail, NULL)) { fprintf(stderr, "peek failed: %lu\n", GetLastError()); return 1; }
            peeks++;                                            /* one more trip into the kernel, for nothing */
            if (avail) { fprintf(stderr, "someone wrote — the demo assumes nobody does\n"); return 1; }
        }
    }
    printf("done: %d pipes, %.0fs, %llu PeekNamedPipe calls, 0 bytes received\n", pipes, secs, peeks);
    io_delta("while waiting", &io0);
    for (int i = 0; i < pipes; i++) { CloseHandle(srv[i]); CloseHandle(cli[i]); }
    return 0;
}
