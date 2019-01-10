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
        compressor_module = importlib.import_module(compressor)

        compression_time_start = time.time()
        compressed = [compressor_module.compress(s) for s in samples]
        compression_time_used = time.time() - compression_time_start

        decompression_time_start = time.time()
        decompressed = [compressor_module.decompress(s) for s in compressed]
        decompression_time_used = time.time() - decompression_time_start
        assert samples == decompressed

        ratios = [100 * len(c) / len(s) for c, s in zip(compressed, samples)]

        stat = {
                'filetype': filetype, 'compressor': compressor,
                'total_compression_time': compression_time_used, 'total_decompression_time': decompression_time_used,
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
html: bz2: total_compression_time=0.02 total_decompression_time=0.01 mean=24.57 stdev=1.91 min=21.59 max=26.36
html: gzip: total_compression_time=0.01 total_decompression_time=0.00 mean=25.43 stdev=1.61 min=22.91 max=26.96
html: lzma: total_compression_time=0.08 total_decompression_time=0.01 mean=23.25 stdev=1.81 min=20.43 max=24.92
html: zlib: total_compression_time=0.01 total_decompression_time=0.00 mean=25.54 stdev=1.59 min=23.05 max=27.05
jpg: bz2: total_compression_time=0.17 total_decompression_time=0.09 mean=98.83 stdev=1.69 min=95.94 max=100.22
jpg: gzip: total_compression_time=0.04 total_decompression_time=0.01 mean=98.72 stdev=2.04 min=95.22 max=99.97
jpg: lzma: total_compression_time=0.35 total_decompression_time=0.02 mean=99.00 stdev=1.90 min=95.64 max=100.05
jpg: zlib: total_compression_time=0.04 total_decompression_time=0.00 mean=98.72 stdev=2.03 min=95.24 max=99.97
"""

