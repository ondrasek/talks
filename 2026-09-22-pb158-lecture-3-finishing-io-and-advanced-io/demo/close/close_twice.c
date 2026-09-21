/* close_twice.c — CloseHandle a handle, then CloseHandle it again. Windows, in C.
 *
 *   close_twice.exe
 *
 * WHAT THIS SHOWS
 *   The Windows twin of close_twice.py. The second CloseHandle on the same
 *   handle value fails with ERROR_INVALID_HANDLE (6): the first call released
 *   it, and the value may already belong to something else in this process.
 *   Microsoft's documentation adds a twist worth seeing live: "If the
 *   application is running under a debugger, the function will throw an
 *   exception if it receives either a handle value that is not valid ... This
 *   can happen if you close a handle twice." NtTrace64 IS a debugger — so under
 *   nmake trace the second close does not fail quietly, it raises.
 *
 * WHAT TO LOOK AT
 *   Untraced: "second CloseHandle: failed, error 6". Traced: NtClose twice, the
 *   second returning STATUS_INVALID_HANDLE (0xC0000008), and the debugger
 *   exception NtTrace reports.
 *
 * WHY IT MATTERS
 *   Same rule as Linux: a failed or repeated close is a bug report, not
 *   something to retry. "An application should call CloseHandle once for each
 *   handle it opens."
 *
 * Build: nmake /f Makefile.msvc     Trace: nmake /f Makefile.msvc trace
 */
#include <windows.h>
#include <stdio.h>
int main(void) {
    HANDLE h = CreateFileA("closed.txt", GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) { fprintf(stderr, "CreateFile: %lu\n", GetLastError()); return 1; }
    DWORD n; WriteFile(h, "one\ntwo\nthree\n", 14, &n, NULL);
    printf("first  CloseHandle: %s\n", CloseHandle(h) ? "ok" : "failed");      /* the handle value is released HERE */
    if (CloseHandle(h)) printf("second CloseHandle: ok (unexpected)\n");        /* "the retry" */
    else printf("second CloseHandle: failed, error %lu (ERROR_INVALID_HANDLE is 6)\n", GetLastError());
    return 0;
}
