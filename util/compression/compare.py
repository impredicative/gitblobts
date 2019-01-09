import importlib
import pathlib
import statistics
from typing import Iterable, List

_COMPRESSORS = ['bz2', 'gzip', 'lzma']


def compare_compressors(samples: Iterable[bytes], compressors: List[str] = _COMPRESSORS):
    stats = []
    for compressor in compressors:
        compress = importlib.import_module(compressor).compress
        ratios = [len(compress(s))/len(s) for s in samples]
        ratios = [r * 100 for r in ratios]
        stat = {
                'compressor': compressor,
                'mean': statistics.mean(ratios), 'stdev': statistics.stdev(ratios),
                'min': min(ratios), 'max': max(ratios),
        }
        stats.append(stat)
        stat = ' '.join(f'{k}={v:.1f}' for k, v in stat.items() if k != 'compressor')
        print(f'{compressor}: {stat}')

    return stats


def test_compressors(filetype: str) -> None:
    path = pathlib.Path(__file__).parent / 'samples' / filetype
    samples = [f.read_bytes() for f in path.glob(f'*.{filetype}')]
    stats = compare_compressors(samples)


if __name__ == '__main__':
    test_compressors('jpg')
