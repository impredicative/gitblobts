import importlib
import pathlib
import statistics
import time
from typing import List

_COMPRESSORS = ['bz2', 'gzip', 'lzma', 'zlib']
# Note: gzip and zlib are effectively the same except for the level of compression.


def compare_compressors(filetype: str, samples: List[bytes], compressors: List[str] = _COMPRESSORS):
    stats = []
    for compressor in compressors:
        compress = importlib.import_module(compressor).compress
        time_start = time.time()
        ratios = [len(compress(s))/len(s) for s in samples]
        time_used = time.time() - time_start
        ratios = [r * 100 for r in ratios]
        stat = {
                'filetype': filetype, 'compressor': compressor, 'total_time': time_used,
                'mean': statistics.mean(ratios), 'stdev': statistics.stdev(ratios),
                'min': min(ratios), 'max': max(ratios),
        }
        stats.append(stat)
        stat = ' '.join(f'{k}={v:.2f}' for k, v in stat.items() if k not in ('filetype, ''compressor'))
        print(f'{filetype}: {compressor}: {stat}')

    return stats


def test_compressors() -> None:
    filetype_dirs = (pathlib.Path(__file__).parent / 'samples').iterdir()
    for path in filetype_dirs:
        samples = [f.read_bytes() for f in path.glob(f'*.{path.name}')]
        compare_compressors(path.name, samples)


if __name__ == '__main__':
    test_compressors()

"""
Results:
html: bz2: total_time=0.02 mean=24.57 stdev=1.91 min=21.59 max=26.36
html: gzip: total_time=0.01 mean=25.43 stdev=1.61 min=22.91 max=26.96
html: lzma: total_time=0.09 mean=23.25 stdev=1.81 min=20.43 max=24.92
jpg: bz2: total_time=0.17 mean=98.83 stdev=1.69 min=95.94 max=100.22
jpg: gzip: total_time=0.04 mean=98.72 stdev=2.04 min=95.22 max=99.97
jpg: lzma: total_time=0.37 mean=99.00 stdev=1.90 min=95.64 max=100.05
"""

