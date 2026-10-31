"""Build the runtime-only Git package and matching reproducible source ZIP.

Tests and scanner evidence remain outside the installable subtree. This builder
never configures or suppresses scanning.
"""
from pathlib import Path
import hashlib
import shutil
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / 'release' / 'hermes-expert-guardian'
FILES = ['__init__.py', 'plugin.yaml', 'pyproject.toml', 'LICENSE']
FILES += [p.relative_to(ROOT).as_posix() for folder in ('guardian', 'desktop', 'dashboard')
          for p in sorted((ROOT / folder).rglob('*'))
          if p.is_file() and p.suffix in {'.py', '.js', '.json'} and '__pycache__' not in p.parts]


def build():
    target = RELEASE.resolve()
    if target.parent != (ROOT / 'release').resolve() or target.name != 'hermes-expert-guardian':
        raise RuntimeError('Release target escaped workspace')
    target.mkdir(parents=True, exist_ok=True)
    expected = set(FILES) | {"README.md"}
    for path in target.rglob("*"):
        if path.is_symlink():
            raise RuntimeError("Symlinks are not allowed in the release tree")
        if path.is_file() and path.relative_to(target).as_posix() not in expected:
            path.unlink()
    for relative in FILES:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    shutil.copyfile(ROOT / 'docs' / 'INSTALL.md', target / 'README.md')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    archive = ROOT / 'dist' / f'hermes-expert-guardian-{version}.zip'
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(target.rglob('*')):
            if path.is_file():
                entry = zipfile.ZipInfo('hermes-expert-guardian/' + path.relative_to(target).as_posix(), (2026, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(entry, path.read_bytes())
    return archive


if __name__ == '__main__':
    archive = build()
    print(archive)
    print('SHA256', hashlib.sha256(archive.read_bytes()).hexdigest())
