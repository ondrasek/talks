/* dest.c — the same fourteen bytes to three destinations, on Windows.
 *
 * WHAT THIS SHOWS
 *   On Linux (Part 8, iodemo) the destination did not change the trace: a file,
 *   a pipe and a socket were all one write(3, ...) call. Windows is the
 *   contrast. The same bytes go three ways from one process, and the KERNEL'S
 *   OWN ACCOUNTING tells you which road each took:
 *
 *     leg 1  WriteFile to a pipe                 -> counted as a WRITE operation   (NtWriteFile)
 *     leg 2  send() on a TCP socket              -> NOT COUNTED AT ALL              (NtDeviceIoControlFile,
 *                                                   control code 0x1201f = IOCTL_AFD_SEND into afd.sys,
 *                                                   on a "fast I/O" path the I/O manager never books)
 *     leg 3  WriteFile on THE SAME socket handle -> counted as a WRITE operation   (NtWriteFile again)
 *
 *   So on Windows the API you pick changes the native call, while the kernel
 *   object underneath is one file object either way (a socket is a file under
 *   \Device\Afd). Linux hides the destination; Windows shows it at the API and
 *   hides it in the kernel.
 *
 * WHAT TO LOOK AT
 *   The "kernel counted" line after each leg. Measured on the VM: leg 1 WRITE +1;
 *   leg 2 nothing — WRITE +0, OTHER +0, the kernel's per-process accounting did
 *   not see your send() as I/O at all; leg 3 WRITE +1. Two WriteFile calls to two
 *   different objects are booked identically; the Winsock call on the same
 *   socket leaves no mark. NtTrace64 (nmake trace) shows the call it did make.
 *
 * ONE MORE LESSON, FOUND ON THE FIRST RUN
 *   WriteFile((HANDLE)sock, ..., NULL) fails with ERROR_INVALID_PARAMETER (87).
 *   Winsock creates sockets as OVERLAPPED handles, and an overlapped handle
 *   demands an OVERLAPPED structure: the file API on a socket is the completion
 *   model whether you asked for it or not (see Part 7). So leg 3 hands it one.
 *
 * Build: nmake /f Makefile.msvc     Trace: nmake /f Makefile.msvc trace
 */
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdio.h>
#pragma comment(lib, "ws2_32.lib")

static const char PAYLOAD[] = "one\ntwo\nthree\n";   /* 14 bytes, exactly what iodemo writes */

/* The kernel's per-process I/O accounting (IO_COUNTERS, winnt.h) — the same
 * counter Lecture 2's iocount read. We snapshot it before each leg and print
 * the difference after: what did the kernel think just happened? */
static IO_COUNTERS io_prev;
static void io_mark(void) { GetProcessIoCounters(GetCurrentProcess(), &io_prev); }
static void io_report(const char *leg) {
    IO_COUNTERS now; GetProcessIoCounters(GetCurrentProcess(), &now);
    printf("  %-22s kernel counted: WRITE ops +%llu   READ ops +%llu   OTHER ops +%llu\n", leg,
           (unsigned long long)(now.WriteOperationCount - io_prev.WriteOperationCount),
           (unsigned long long)(now.ReadOperationCount  - io_prev.ReadOperationCount),
           (unsigned long long)(now.OtherOperationCount - io_prev.OtherOperationCount));
    io_prev = now;
}

int main(void) {
    DWORD n; char in[64]; int got;

    /* ---- leg 1: a pipe, through the file API --------------------------------- */
    HANDLE rd, wr;
    if (!CreatePipe(&rd, &wr, NULL, 0)) { fprintf(stderr, "CreatePipe: %lu\n", GetLastError()); return 1; }
    io_mark();
    WriteFile(wr, PAYLOAD, 14, &n, NULL);            /* one write operation, one NtWriteFile */
    io_report("1 pipe, WriteFile");
    ReadFile(rd, in, sizeof in, &n, NULL);
    printf("pipe:              WriteFile wrote 14, ReadFile got %lu\n\n", n);
    CloseHandle(rd); CloseHandle(wr);

    /* ---- leg 2: a TCP socket, through Winsock ---------------------------------
     * Listener, client and accepted peer all live in this process on loopback,
     * so the demo needs no second program and no network. */
    WSADATA w; WSAStartup(MAKEWORD(2, 2), &w);
    SOCKET ls = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {0}; a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK); a.sin_port = 0;
    bind(ls, (struct sockaddr *)&a, sizeof a); listen(ls, 1);
    int alen = sizeof a; getsockname(ls, (struct sockaddr *)&a, &alen);
    SOCKET cs = socket(AF_INET, SOCK_STREAM, 0);
    connect(cs, (struct sockaddr *)&a, sizeof a);
    SOCKET ps = accept(ls, NULL, NULL);
    io_mark();
    int sent = send(cs, PAYLOAD, 14, 0);              /* Winsock -> afd.sys by device control on a fast path: not booked as I/O at all */
    io_report("2 socket, send()");
    got = recv(ps, in, sizeof in, 0);
    printf("socket, send():    send wrote %d, recv got %d\n\n", sent, got);

    /* ---- leg 3: the SAME socket, through the file API -------------------------
     * A SOCKET is a kernel file handle underneath, so WriteFile accepts it. But
     * it is an overlapped handle, so WriteFile needs an OVERLAPPED and we must
     * wait for the result ourselves — completion-model rules (Part 7). */
    OVERLAPPED ov = {0}; ov.hEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    n = 0;
    io_mark();
    BOOL ok = WriteFile((HANDLE)cs, PAYLOAD, 14, &n, &ov);
    if (!ok && GetLastError() == ERROR_IO_PENDING) ok = GetOverlappedResult((HANDLE)cs, &ov, &n, TRUE);
    io_report("3 socket, WriteFile");
    if (!ok) printf("socket, WriteFile: failed: %lu\n", GetLastError());
    else { got = recv(ps, in, sizeof in, 0); printf("socket, WriteFile: WriteFile wrote %lu, recv got %d\n", n, got); }
    CloseHandle(ov.hEvent);

    closesocket(cs); closesocket(ps); closesocket(ls); WSACleanup();
    return 0;
}
