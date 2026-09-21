/* wait_iocp.c — a hundred pipes nobody writes to, ONE wait. COMPLETION, on Windows, in C.
 *
 *   wait_iocp.exe [PIPES=100] [SECS=2]
 *
 * WHAT THIS SHOWS
 *   The Windows twin of wait_epoll.py — but a different MODEL. Linux's epoll is
 *   READINESS: the kernel says "you may read now" and the program then reads.
 *   Windows' native model is COMPLETION: the program hands the kernel a buffer
 *   up front ("read into this when something arrives"), binds the handle to an
 *   I/O completion port, and blocks ONCE in GetQueuedCompletionStatus until the
 *   kernel says "done, I read it for you". Nothing arrives here, so the one wait
 *   sleeps to its timeout — and that single sleeping call is the whole cost of
 *   waiting on a hundred pipes.
 *
 * WHAT TO LOOK AT
 *   1. "one GetQueuedCompletionStatus slept 2.00s" — one call, two seconds,
 *      against wait_peek.exe's hundreds of thousands.
 *   2. The "kernel counted" line: while waiting, the kernel counted almost
 *      nothing for this process, because the program did nothing.
 *   3. Under NtTrace64 (nmake trace): 100 NtReadFile SUBMISSIONS before the
 *      wait (the kernel now owns the hundred buffers), one NtRemoveIoCompletion
 *      returning STATUS_TIMEOUT, then 100 NtCancelIoFileEx on the way out. In a
 *      trace, "no reads of your own, but completions" is the tell for this
 *      model, as objective 2 says.
 *
 * WHY IT MATTERS
 *   Who owns the buffer while waiting is the real difference between the two
 *   models (Part 7): here the kernel does, which is why the buffer must exist
 *   before the data does and must not be touched until the completion arrives.
 *
 * Build: nmake /f Makefile.msvc     (x64 Developer Command Prompt)
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

static void io_delta(const char *what, const IO_COUNTERS *before) {   /* the kernel's own accounting, as a difference */
    IO_COUNTERS now; GetProcessIoCounters(GetCurrentProcess(), &now);
    printf("%s: kernel counted READ ops +%llu, OTHER ops +%llu\n", what,
           (unsigned long long)(now.ReadOperationCount  - before->ReadOperationCount),
           (unsigned long long)(now.OtherOperationCount - before->OtherOperationCount));
}

int main(int argc, char **argv) {
    int pipes = argc > 1 ? atoi(argv[1]) : 100;
    double secs = argc > 2 ? atof(argv[2]) : 2.0;

    /* ONE completion port. Every pipe's completions will be queued here. */
    HANDLE port = CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, 0, 0);
    HANDLE *srv = calloc(pipes, sizeof(HANDLE)), *cli = calloc(pipes, sizeof(HANDLE));
    OVERLAPPED *ov = calloc(pipes, sizeof(OVERLAPPED));       /* one per outstanding read: the kernel's bookmark */
    char (*buf)[64] = calloc(pipes, 64);                       /* one buffer per pipe — handed to the kernel below */
    char name[64];

    for (int i = 0; i < pipes; i++) {
        snprintf(name, sizeof name, "\\\\.\\pipe\\pb158-iocp-c-%d", i);
        /* FILE_FLAG_OVERLAPPED: this handle may have operations in flight. */
        srv[i] = CreateNamedPipeA(name, PIPE_ACCESS_INBOUND | FILE_FLAG_OVERLAPPED, PIPE_TYPE_BYTE | PIPE_WAIT, 1, 4096, 4096, 0, NULL);
        cli[i] = CreateFileA(name, GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
        if (srv[i] == INVALID_HANDLE_VALUE || cli[i] == INVALID_HANDLE_VALUE) { fprintf(stderr, "pipe %d failed: %lu\n", i, GetLastError()); return 1; }
        ConnectNamedPipe(srv[i], NULL);
        /* Bind: completions for this pipe go to the port, tagged with i. */
        CreateIoCompletionPort(srv[i], port, (ULONG_PTR)i, 0);
        /* SUBMIT the read now. It cannot complete (nobody writes), so it returns
         * ERROR_IO_PENDING and the kernel keeps buf[i] until it does. */
        if (!ReadFile(srv[i], buf[i], 64, NULL, &ov[i]) && GetLastError() != ERROR_IO_PENDING) {
            fprintf(stderr, "ReadFile %d failed: %lu\n", i, GetLastError()); return 1;
        }
    }

    IO_COUNTERS io0; GetProcessIoCounters(GetCurrentProcess(), &io0);
    LARGE_INTEGER f, t0, t1; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t0);

    /* THE ONE CALL THE LECTURE IS ABOUT: sleep until any of the hundred reads
     * completes, or the timeout passes. Nobody writes, so: timeout. */
    DWORD bytes = 0; ULONG_PTR key = 0; LPOVERLAPPED done = NULL;
    BOOL ok = GetQueuedCompletionStatus(port, &bytes, &key, &done, (DWORD)(secs * 1000));
    QueryPerformanceCounter(&t1);
    double waited = (double)(t1.QuadPart - t0.QuadPart) / (double)f.QuadPart;
    if (!ok && done == NULL && GetLastError() == WAIT_TIMEOUT)
        printf("done: %d pipes, one GetQueuedCompletionStatus slept %.2fs, 0 completions, 0 bytes\n", pipes, waited);
    else
        printf("unexpected completion: key=%llu bytes=%lu\n", (unsigned long long)key, bytes);
    io_delta("while waiting", &io0);

    /* Take the buffers back: cancel the outstanding reads before freeing anything. */
    for (int i = 0; i < pipes; i++) { CancelIoEx(srv[i], &ov[i]); CloseHandle(srv[i]); CloseHandle(cli[i]); }
    CloseHandle(port);
    return 0;
}
