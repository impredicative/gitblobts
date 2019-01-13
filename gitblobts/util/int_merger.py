from typing import Tuple
import unittest


class IntMerger:
    """Reversibly encode two integers into a single integer.

    Only the first integer can be signed (possibly negative). The second
    integer must be unsigned (always non-negative).

    In the merged integer, the left bits are of the first input integer, and
    the right bits are of the second input integer.
    """
    # Ref: https://stackoverflow.com/a/54164324/
    def __init__(self, num_bits_int2: int):
        """
        :param num_bits_int2: Max bit length of second integer.
        """
        self._num_bits_int2: int = num_bits_int2
        self._max_int2: int = self._max_int(self._num_bits_int2)

    @staticmethod
    def _max_int(num_bits: int) -> int:
        return (1 << num_bits) - 1

    def merge(self, int1: int, int2: int) -> int:
        return (int1 << self._num_bits_int2) | int2

    def split(self, int12: int) -> Tuple[int, int]:
        int1 = int12 >> self._num_bits_int2
        int2 = int12 & self._max_int2
        return int1, int2


class TestIntMerger(unittest.TestCase):
    def test_intmerger(self):
        max_num_bits = 8
        for num_bits_int1 in range(max_num_bits + 1):
            for num_bits_int2 in range(max_num_bits + 1):
                expected_merged_max_num_bits = num_bits_int1 + num_bits_int2
                merger = IntMerger(num_bits_int2)
                maxint1 = (+1 << num_bits_int1) - 1
                minint1 = (-1 << num_bits_int1) + 1
                for int1 in range(minint1, maxint1 + 1):
                    for int2 in range(1 << num_bits_int2):
                        int12 = merger.merge(int1, int2)
                        # print(f'{int1} ({num_bits_int1}b), {int2} ({num_bits_int2}b) = {int12} ({int12.bit_length()}b)')
                        self.assertLessEqual(int12.bit_length(), expected_merged_max_num_bits)
                        self.assertEqual((int1, int2), merger.split(int12))
                self.assertEqual(int12.bit_length(), expected_merged_max_num_bits)


if __name__ == '__main__':
    unittest.main()
