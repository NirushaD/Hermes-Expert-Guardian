"""Build a clean installable Git-tree archive without local runtime references."""
from pathlib import Path
import hashlib
import zipfile
root=Path(__file__).resolve().parent
files=[root/p for p in ['__init__.py','plugin.yaml','pyproject.toml','README.md','LICENSE','package.py']]
for folder in ['guardian','desktop','dashboard','docs','tests']:
    files += [p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.json','.md'}]
archive=root/'dist'/'hermes-expert-guardian-0.1.0.zip'
archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(files):z.write(path,'hermes-expert-guardian/'+path.relative_to(root).as_posix())
print(archive)
print('SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())

