"""Offline CLI smoke/byte reproducibility check; run as python -m tests.qualify_ha."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(*args):
    subprocess.run([sys.executable,'-m','building_ops',*args],check=True,stdout=subprocess.DEVNULL)


def main():
    mapping=Path('tests/fixtures/gardena_ha/mapping.json')
    run('gardena-ha','check-mapping','--mapping',str(mapping))
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        for kind in ('rate','cumulative'):
            cfg=json.loads(mapping.read_text())
            cfg['devices'][0]['flow']['kind']=kind
            config=root/f'{kind}.json';config.write_text(json.dumps(cfg))
            output=root/f'{kind}-report'
            args=('gardena-ha','replay','--input',f'tests/fixtures/gardena_ha/{kind}.jsonl',
                  '--mapping',str(config),'--synthetic','--out',str(output))
            run(*args)
            first={p.name:p.read_bytes() for p in output.iterdir()}
            run('check',str(output/'decisions.jsonl'),'--strict-safety')
            # Re-use the exact source/output paths after removing only task-owned
            # temporary results: reports contain their source provenance.
            for path in output.iterdir():path.unlink()
            run(*args)
            second={p.name:p.read_bytes() for p in output.iterdir()}
            if first!=second:raise AssertionError(f'{kind} replay is not byte deterministic')
            if not (output/'decisions.jsonl').read_text().strip():raise AssertionError('positive control generated no finding')
    print('HA rate/cumulative CLI replay: deterministic; strict safety accepted')


if __name__=='__main__':main()
