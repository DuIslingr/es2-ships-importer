"""Parallel work for the build, as the GoF3 importer does it: the image writes (PNG / JPEG encoding, most of the build's time:
2048 px maps saved with optimize) and the per-ship steps run on worker threads (Pillow, NumPy and zlib let go of the GIL).

Workers: --jobs, else half the CPUs, fewer when the memory available is short (JOB_GB each, 4 GB kept back): every core at
once froze the machine in the GoF3 build. The process also runs at a lower priority (import.py), so the desktop stays usable.

write_image() queues an image and returns at once (at most a few per worker wait, so the arrays don't pile up in memory);
code that reads a written file back calls wait(path) first, and exists(path) counts a queued file as there. flush() waits
for everything (build.main before the mod's own files). The output is the same file for file as one thread would write."""
import os, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

JOBS = None      # --jobs
JOB_GB = 1.0     # memory a worker may take (a few 2048 px maps in flight)
_pool = None     # the image writes
_tasks = None    # run(): per-ship steps (their own pool: a step that queues writes must never wait on its own workers)
_lock = threading.Lock()
_pending = {}    # path -> future
_slots = None


def workers():
    if JOBS: return max(1, JOBS)
    try:
        avail = next(int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemAvailable:")) / 1024 ** 2
    except (OSError, StopIteration):
        avail = 8.0
    return max(1, min((os.cpu_count() or 4) // 2, int((avail - 4) / JOB_GB)))


def pool():
    global _pool, _slots
    with _lock:
        if _pool is None:
            n = workers()
            _pool = ThreadPoolExecutor(n, thread_name_prefix='build')
            _slots = threading.BoundedSemaphore(n * 3)
    return _pool


def lower_priority():
    """The build at a lower priority (Unix nice 10, Windows below normal)."""
    try:
        os.nice(10)
    except (AttributeError, OSError):
        try:
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
        except Exception:
            pass


def _write(path, arr, size, square, kw):
    try:
        im = Image.fromarray(arr)
        if square and size and im.size[0] > size:
            im = im.resize((size, size), Image.LANCZOS)
        elif size and not square and max(im.size) > size:
            s = size / max(im.size)
            im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
        im.save(path, **kw)
    finally:
        _slots.release()


def write_image(path, arr, size=None, square=False, **save):
    """Saves 'arr' (a NumPy image, copied) to 'path' on a worker, shrunk to 'size' on its longest side if larger (square:
    to size x size when wider, build.save's rule); 'save' goes to Image.save (default optimize=True)."""
    if not save: save = {'optimize': True}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    p = pool()
    _slots.acquire()
    f = p.submit(_write, path, np.array(arr, copy=True), size, square, save)
    with _lock:
        _pending[path] = f
    return path


def wait(path):
    """Blocks until a queued write of 'path' is done (its error raised here)."""
    with _lock:
        f = _pending.get(path)
    if f is not None: f.result()


def exists(path):
    with _lock:
        if path in _pending: return True
    return os.path.exists(path)


def flush():
    """Waits for every queued write; the first error is raised."""
    with _lock:
        fs = list(_pending.values())
    for f in fs: f.result()


def run(fn, items):
    """fn over items on worker threads, the results in the items' order."""
    global _tasks
    with _lock:
        if _tasks is None: _tasks = ThreadPoolExecutor(workers(), thread_name_prefix='step')
    return list(_tasks.map(fn, items))


def submit(fn, *a):
    """fn(*a) on a worker thread: its future."""
    global _tasks
    with _lock:
        if _tasks is None: _tasks = ThreadPoolExecutor(workers(), thread_name_prefix='step')
    return _tasks.submit(fn, *a)


_once_lock = threading.Lock()
_once = {}

def once(key):
    """A lock for 'key': the first thread makes the thing, the others wait and take it from the cache."""
    with _once_lock:
        l = _once.get(key)
        if l is None: l = _once[key] = threading.Lock()
        return l
