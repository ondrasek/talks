/* iocost.c — what the last handoff costs, on Windows. The C twin of save.py's four modes.
 *
 *   iocost.exe MODE [RECORDS=100]          MODE = default | flush | writethrough | nobuffer
 *
 * WHAT THIS SHOWS
 *   A program that "saves a file" can stop at four different places in the
 *   four-level buffer stack, and each stop has a price:
 *
 *     default       WriteFile into the system cache; the lazy writer flushes later.
 *                   Cheap: the bytes are the kernel's problem now, not the disk's.
 *     flush         WriteFile, then FlushFileBuffers, per record — the fsync() twin:
 *                   ask the kernel to push the record to the DEVICE and wait for it.
 *     writethrough  FILE_FLAG_WRITE_THROUGH: every WriteFile goes through to the
 *                   device before it returns. Same price as flush, paid per call.
 *     nobuffer      FILE_FLAG_NO_BUFFERING: bypass the cache; sizes and buffers must be
 *                   sector-aligned (hence 4096-byte records and _aligned_malloc).
 *
 * WHAT TO LOOK AT
 *   1. Wall time per mode. On the VM: 0.7 ms cached against 27.9 ms with a flush
 *      per record — FORTY times, for asking the device to confirm each record.
 *      Linux's save.py showed the same shape (1.1 ms against 67.3 ms).
 *   2. "kernel write operations: 100" in EVERY mode. The kernel's own accounting
 *      (GetProcessIoCounters, the counter Lecture 2 used) says how many times the
 *      program asked; only the wall time says who waited.
 *   3. Under NtTrace64 (nmake trace): flush is 100 NtWriteFile + 100
 *      NtFlushBuffersFile; default is 100 NtWriteFile and no flush at all.
 *
 * WHY IT MATTERS
 *   This is why programs that are not databases never flush per record, and why
 *   the sentence from Lecture 2 stands: the only real durability answer, still
 *   best effort, is a tested UPS.
 *
 * Build (x64 Developer Command Prompt):  nmake /f Makefile.msvc
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "default";
    int records = argc > 2 ? atoi(argv[2]) : 100;
    const DWORD rec = 4096;
    DWORD flags = FILE_ATTRIBUTE_NORMAL;
    if (!strcmp(mode, "writethrough")) flags |= FILE_FLAG_WRITE_THROUGH;   /* each WriteFile waits for the device */
    else if (!strcmp(mode, "nobuffer")) flags |= FILE_FLAG_NO_BUFFERING;   /* skip the cache entirely */
    else if (strcmp(mode, "default") && strcmp(mode, "flush")) {
        fprintf(stderr, "unknown mode %s\n", mode); return 2;
    }
    /* Sector-aligned buffer: required by FILE_FLAG_NO_BUFFERING, harmless otherwise. */
    char *buf = (char *)_aligned_malloc(rec, 4096);
    if (!buf) { fprintf(stderr, "alloc failed\n"); return 2; }
    memset(buf, 'x', rec); memcpy(buf, "record ", 7); buf[rec - 1] = '\n';

    HANDLE h = CreateFileA("saved.bin", GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, flags, NULL);
    if (h == INVALID_HANDLE_VALUE) { fprintf(stderr, "CreateFile failed: %lu\n", GetLastError()); return 1; }

    IO_COUNTERS before, after; LARGE_INTEGER f, t0, t1;
    GetProcessIoCounters(GetCurrentProcess(), &before);          /* the kernel's own count of this process's writes */
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t0);
    for (int i = 0; i < records; i++) {
        DWORD written = 0;
        if (!WriteFile(h, buf, rec, &written, NULL) || written != rec) {
            fprintf(stderr, "WriteFile failed at record %d: %lu\n", i, GetLastError()); return 1;
        }
        if (!strcmp(mode, "flush") && !FlushFileBuffers(h)) {            /* level 3 -> level 4, and wait: the fsync twin */
            fprintf(stderr, "FlushFileBuffers failed: %lu\n", GetLastError()); return 1;
        }
    }
    QueryPerformanceCounter(&t1);
    CloseHandle(h);
    GetProcessIoCounters(GetCurrentProcess(), &after);
    double ms = (double)(t1.QuadPart - t0.QuadPart) * 1000.0 / (double)f.QuadPart;
    printf("done: %d records x %lu B, mode=%s, %.1f ms, kernel write operations: %llu\n",
           records, rec, mode, ms, (unsigned long long)(after.WriteOperationCount - before.WriteOperationCount));
    _aligned_free(buf);
    return 0;
}
