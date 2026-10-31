"""Content fingerprints and verified stage snapshots for import.py (stdlib only)."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

SCHEMA = 1


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    """Interrupted writes must never turn incomplete work into a cache hit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def recipe(root, entries):
    """Follow local Python imports and literal helper-script names, including Blender subprocesses.

    Include importer orchestration and this helper in every recipe; follow conversion tables too.
    Third-party imports are represented separately by the caller's environment identity.
    """
    root = Path(root)
    tools = root / 'tools'
    pending = [root / 'import.py', tools / 'build_cache.py'] + [tools / p for p in entries]
    files = {}
    while pending:
        path = pending.pop()
        rel = path.relative_to(root).as_posix()
        if rel in files or not path.is_file():
            continue
        files[rel] = file_hash(path)
        if path.suffix != '.py' or path == root / 'import.py' or path in (tools / 'build_cache.py', tools / 'import_pipeline.py'):
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pending.extend(tools / (n.name.split('.')[0] + '.py') for n in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                pending.append(tools / (node.module.split('.')[0] + '.py'))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Scripts invoked by subprocess are not Python imports.
                if node.value.endswith(('.py', '.json', '.txt')) and '/' not in node.value and '\\' not in node.value:
                    pending.append(tools / node.value)
    return dict(sorted(files.items()))


def stage(root, entries, inputs, options=None):
    code = recipe(root, entries)
    return {'fingerprint': digest({'schema': SCHEMA, 'code': code, 'inputs': inputs, 'options': options}),
            'code': code, 'inputs': inputs, 'options': options}


def revision(root):
    try:
        r = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        return None


def inventory(path):
    """Hash contents, names and directories, including additions/removals and same-size edits."""
    path = Path(path)
    if path.is_file():
        return {'kind': 'file', 'sha256': file_hash(path)}
    if not path.is_dir():
        return {'kind': 'missing'}
    files, directories = {}, []
    for base, dirs, names in os.walk(path):
        dirs.sort()
        directories.extend((Path(base) / d).relative_to(path).as_posix() for d in dirs)
        for name in sorted(names):
            p = Path(base) / name
            files[p.relative_to(path).as_posix()] = file_hash(p)
    return {'kind': 'directory', 'directories': directories, 'files': files}


def executable(command):
    """Identify the actual executable, rather than trusting a path or version label alone."""
    import shutil
    if not command:
        return None
    resolved = shutil.which(str(command))
    if resolved is None and Path(command).is_file():
        resolved = str(Path(command).absolute())
    return {'path': resolved, 'sha256': file_hash(resolved) if resolved else None}


def copy_files(source, destination, paths=None):
    """Copies, never hard-links: later stages can rewrite their inputs without changing a snapshot."""
    import shutil
    source, destination = Path(source), Path(destination)
    if paths is None:
        paths = [p.relative_to(source) for p in source.rglob('*') if p.is_file()]
    for relative in paths:
        src, dst = source / relative, destination / relative
        if not src.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def disjoint(paths):
    """Work and output directories must not overlap inputs, one another, or source code."""
    pairs = list(paths.items())
    for i, (label, path) in enumerate(pairs):
        if path is None:
            continue
        p = Path(path).resolve()
        for other_label, other_path in pairs[i + 1:]:
            if other_path is None:
                continue
            q = Path(other_path).resolve()
            if p == q or p in q.parents or q in p.parents:
                raise ValueError(f'{label} and {other_label} must not overlap: {p} / {q}')


class Work:
    """Owned cache folder with an exclusive lock and verified, immutable stage snapshots."""
    def __init__(self, path, fresh=False):
        self.path = Path(path)
        self.fresh = fresh
        self.records = {}

    def __enter__(self):
        import shutil
        self.path.mkdir(parents=True, exist_ok=True)
        owner = self.path / 'es2-cache.json'
        if owner.exists():
            try:
                owned = json.loads(owner.read_text(encoding='utf-8')).get('id') == 'es2_import_cache'
            except (ValueError, AttributeError):
                owned = False
            if not owned:
                raise ValueError(f'{self.path} is not an ES2 importer work folder')
        elif any(p.name != '.lock' for p in self.path.iterdir()):
            raise ValueError(f'{self.path} is not an empty ES2 importer work folder; choose another --work')
        # Advisory locks are released by the OS on failure, including a killed process.
        # Keep the file in place: unlinking a locked inode would let a second process bypass it.
        self.lock = open(self.path / '.lock', 'a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise ValueError(f'another importer is using {self.path}')
        try:
            if not owner.exists(): write_json(owner, {'id': 'es2_import_cache', 'schema': SCHEMA})
            if self.fresh:
                try: shutil.rmtree(self.path / 'stages')
                except FileNotFoundError: pass
            return self
        except BaseException:
            self.lock.close()
            raise

    def __exit__(self, *exc):
        self.lock.close()

    def run(self, name, recipe, produce):
        """A failed/partial result is usable for this build, but is retried on the next run."""
        import shutil
        directory = self.path / 'stages' / name
        files = directory / 'files'
        record_path = directory / 'record.json'
        try:
            saved = json.loads(record_path.read_text(encoding='utf-8'))
            valid = (saved.get('schema') == SCHEMA and saved.get('fingerprint') == recipe['fingerprint']
                     and isinstance(saved.get('result'), dict) and files.is_dir())
            # A mismatched recipe cannot be reused: avoid reading the old payload before discarding it.
            if valid:
                outputs = inventory(files)
                valid = saved.get('outputs') == outputs
        except (OSError, ValueError, AttributeError):
            valid = False
        if valid:
            print(f'  {name}: reused')
            result = saved['result']
        else:
            print(f'  {name}: building')
            try: shutil.rmtree(directory)
            except FileNotFoundError: pass
            files.mkdir(parents=True)
            try:
                result = produce(files)
                outputs = inventory(files)
                if result.get('reusable', True):
                    write_json(record_path, {'schema': SCHEMA, 'fingerprint': recipe['fingerprint'],
                                             'outputs': outputs, 'result': result})
            except BaseException:
                shutil.rmtree(directory, ignore_errors=True)
                raise
        self.records[name] = dict(recipe, reused=valid, result=result, outputs=outputs)
        return files, result

