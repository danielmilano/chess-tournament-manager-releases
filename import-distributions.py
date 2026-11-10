import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse

assets = json.loads(Path('distributions.json').read_text())
with tempfile.TemporaryDirectory() as work:
    for tag in sorted({a['tag'] for a in assets}):
        group = [a for a in assets if a['tag'] == tag]
        directory = Path(work) / tag
        directory.mkdir()
        for asset in group:
            source = 'https://chesstournamentmanagerpro.com' + asset['source']
            assert urlparse(source).netloc == 'chesstournamentmanagerpro.com'
            target = directory / Path(asset['source']).name
            subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--retry', '3', '--max-time', '300', source, '-o', str(target)], check=True)
            assert target.stat().st_size == asset['size'], target.name
            assert hashlib.sha256(target.read_bytes()).hexdigest() == asset['sha256'], target.name
            print('Verified ' + target.name, flush=True)
        checks = directory / 'SHA256SUMS.txt'
        checks.write_text(''.join(a['sha256'] + '  ' + Path(a['source']).name + '\n' for a in group))
        existing = subprocess.run(['gh', 'release', 'view', tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if existing.returncode:
            command = ['gh', 'release', 'create', tag, '--draft', '--title', 'Chess Tournament Manager Pro ' + tag.removeprefix('desktop-'), '--notes', 'Verified desktop distribution files. macOS packages are signed and notarized; Windows MSI files are unsigned and require Windows x64. Installation information: https://chesstournamentmanagerpro.com/ . SHA-256 checksums accompany the assets.']
            if tag.endswith('.98'):
                command += ['--prerelease']
            subprocess.run(command, check=True)
        listing = json.loads(subprocess.check_output(['gh', 'release', 'view', tag, '--json', 'assets'], text=True))
        uploaded = {a['name']: a for a in listing['assets']}
        for target in directory.iterdir():
            if target.name in uploaded:
                # A different or incomplete asset must not be silently replaced.
                assert uploaded[target.name]['size'] == target.stat().st_size, target.name
                continue
            subprocess.run(['gh', 'release', 'upload', tag, str(target)], check=True)
        subprocess.run(['gh', 'release', 'edit', tag, '--draft=false', '--latest=false'], check=True)
        print('Published ' + tag, flush=True)
