"""Install a complete notebook while preserving unrelated files in its output folder."""

from contextlib import contextmanager
import os
import shutil


@contextmanager
def writer_lock(folder):
    if os.name == "nt":
        import msvcrt

        with (folder / ".notebook.lock").open("a+b") as lock:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fd = os.open(folder, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def publish(staged, output):
    files = sorted(p.relative_to(staged) for p in staged.rglob("*") if p.is_file())
    backup = staged.parent / "previous"
    output.mkdir(parents=True, exist_ok=True)
    with writer_lock(output):
        for rel in files:
            dest = output / rel
            if dest.is_symlink() or dest.parent.resolve() != dest.parent:
                raise ValueError(f"Output uses a symbolic link: {rel}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if not dest.is_file():
                    raise ValueError(f"Expected an output file: {rel}")
                old = backup / rel
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, old)
        installed = []
        try:
            for rel in files:
                os.replace(staged / rel, output / rel)
                installed.append(rel)
        except OSError:
            for rel in reversed(installed):
                if (backup / rel).exists():
                    os.replace(backup / rel, output / rel)
                else:
                    (output / rel).unlink()
            raise
