/*
 * iodemo.c — the smallest program that makes a trace worth reading.
 *
 * PB158 Lecture 2, section 5. The same source is compiled and traced on both
 * Linux and Windows, so every difference between the two traces belongs to the
 * operating system rather than to the program.
 *
 * It prints nothing. That is deliberate: console output on Windows travels
 * through the console subsystem, which is a different path from file I/O and
 * would put lines in the trace that have nothing to do with the lesson. The
 * program is silent and the trace does the talking.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#endif

/*
 * How many write operations the operating system has counted for this
 * process — from the kernel's own per-process counters, not from a tracer.
 *   Linux:   /proc/self/io, field `syscw`  ("number of write syscalls",
 *            proc_pid_io(5)).
 *   Windows: GetProcessIoCounters -> IO_COUNTERS.WriteOperationCount
 *            ("the number of write operations performed", winnt.h).
 * Returns -1 where neither exists.
 */
static long long write_operations(void)
{
#ifdef _WIN32
    IO_COUNTERS io;
    if (!GetProcessIoCounters(GetCurrentProcess(), &io)) {
        return -1;
    }
    return (long long)io.WriteOperationCount;
#else
    FILE *stats = fopen("/proc/self/io", "r");
    char line[128];
    long long n = -1;
    if (stats == NULL) {
        return -1;
    }
    while (fgets(line, sizeof line, stats) != NULL) {
        if (strncmp(line, "syscw:", 6) == 0) {
            n = strtoll(line + 6, NULL, 10);
        }
    }
    fclose(stats);
    return n;
#endif
}

int main(int argc, char **argv)
{
    /* `--count` reports the kernel's write-operation count at the end. Off by
     * default: the report is itself a write to the console and would show up
     * in a trace as one more line. */
    const char *path = "iodemo.out";
    int report = 0;
    FILE *f;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--count") == 0) {
            report = 1;
        } else {
            path = argv[i];
        }
    }

    /* 1. One deliberate failure. This file does not exist, and it is not
     *    supposed to. On Windows the trace shows an NTSTATUS together with the
     *    Win32 error it translates into; on Linux it shows a single errno.
     *    Without a failure both traces are success all the way down and that
     *    difference never appears. */
    f = fopen("no-such-file.txt", "rb");
    if (f != NULL) {
        fclose(f);
        return 2;           /* the file existed after all — start over */
    }

    /* 2. The file we mean to write. */
    f = fopen(path, "wb");
    if (f == NULL) {
        return 1;
    }

    /* 3. Three writes in the source. Fourteen bytes. Watch how many system
     *    calls arrive in the trace. */
    fwrite("one\n",   1, 4, f);
    fwrite("two\n",   1, 4, f);
    fwrite("three\n", 1, 6, f);

    /* 4. fclose flushes first, then closes. The flush is where the bytes
     *    leave the program — and therefore where a failure from ANY of the
     *    three fwrite calls above finally surfaces, attached to none of them.
     *
     *    Checking this return value is the point of section 6. Almost no code
     *    does, which is the difference between having written fourteen bytes
     *    and believing you did. */
    if (fclose(f) != 0) {
        return 3;
    }

    if (report) {
        long long n = write_operations();
        if (n < 0) {
            fprintf(stderr, "write operations counted by the kernel: unavailable on this platform\n");
        } else {
            fprintf(stderr, "write operations counted by the kernel: %lld\n", n);
        }
    }

    return 0;
}
