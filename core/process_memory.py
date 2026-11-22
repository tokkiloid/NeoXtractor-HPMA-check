"""Read this process's Windows private commit; no privileged system queries."""

import ctypes
import sys
from time import monotonic


def private_memory_bytes():
    if sys.platform != "win32":
        return None
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
                "PrivateUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return counters.PrivateUsage


class ScanMemoryLimitExceeded(Exception):
    pass


SCAN_MEMORY_LIMIT = 768 * 1024 * 1024
_next_check = 0.0
_baseline = 0  # private memory when the current pack load or scan began (see begin_scan)


def begin_scan():
    """
    Count from here: the guard limits what the pack load or scan starting now adds, not the memory other features
    (an open or recently closed creator, the Scene Viewer) already hold.
    """
    global _baseline, _next_check
    _baseline = private_memory_bytes() or 0
    _next_check = 0.0


def check_scan_memory(force=False):
    """Cooperative safety check, not a hard OS limit or a preview-memory cap."""
    global _next_check
    now = monotonic()
    if not force and now < _next_check:
        return
    _next_check = now + 0.1
    usage = private_memory_bytes()
    if usage is not None and usage - _baseline > SCAN_MEMORY_LIMIT:
        raise ScanMemoryLimitExceeded(
            "Scan stopped: it needed more than 768 MiB of memory. Close extra viewer windows, unload the archive, "
            "or open a single copy. No game files were changed."
        )
