from typing import Callable, Optional
import base64
import unittest


class IntBaseEncoder:
    """Reversibly encode an unsigned or signed integer into a customizable encoding of a variable or fixed length."""
    # Ref: https://stackoverflow.com/a/54152763/
    def __init__(self, encoding: str, *, bits: Optional[int] = None, signed: bool = False):
        """
        :param encoder: Name of encoding from base64 module, e.g. b64, urlsafe_b64, b32, b16, etc.
        :param bits: Max bit length of int which is to be encoded. If specified, the encoding is of a fixed length,
        otherwise of a variable length.
        :param signed: If True, integers are considered signed, otherwise unsigned.
        """
        self._decoder: Callable[[bytes], bytes] = getattr(base64, f'{encoding}decode')
        self._encoder: Callable[[bytes], bytes] = getattr(base64, f'{encoding}encode')
        self.signed: bool = signed
        self.bytes_length: Optional[int] = bits and self._bytes_length(2 ** bits - 1)

    def _bytes_length(self, i: int) -> int:
        return (i.bit_length() + 7 + self.signed) // 8

    def encode(self, i: int) -> bytes:
        length = self.bytes_length or self._bytes_length(i)
        i_bytes = i.to_bytes(length, byteorder='big', signed=self.signed)
        return self._encoder(i_bytes)

    def decode(self, b64: bytes) -> int:
        i_bytes = self._decoder(b64)
        return int.from_bytes(i_bytes, byteorder='big', signed=self.signed)


class TestIntBaseEncoder(unittest.TestCase):

    ENCODINGS = ('b85', 'b64', 'urlsafe_b64', 'b32', 'b16')

    def test_unsigned_with_variable_length(self):
        for encoding in self.ENCODINGS:
            encoder = IntBaseEncoder(encoding)
            previous_length = 0
            for i in range(1234):
                encoded = encoder.encode(i)
                self.assertGreaterEqual(len(encoded), previous_length)
                self.assertEqual(i, encoder.decode(encoded))

    def test_signed_with_variable_length(self):
        for encoding in self.ENCODINGS:
            encoder = IntBaseEncoder(encoding, signed=True)
            previous_length = 0
            for i in range(-1234, 1234):
                encoded = encoder.encode(i)
                self.assertGreaterEqual(len(encoded), previous_length)
                self.assertEqual(i, encoder.decode(encoded))

    def test_unsigned_with_fixed_length(self):
        for encoding in self.ENCODINGS:
            for maxint in range(257):
                encoder = IntBaseEncoder(encoding, bits=maxint.bit_length())
                maxlen = len(encoder.encode(maxint))
                for i in range(maxint + 1):
                    encoded = encoder.encode(i)
                    self.assertEqual(len(encoded), maxlen)
                    self.assertEqual(i, encoder.decode(encoded))

    def test_signed_with_fixed_length(self):
        for encoding in self.ENCODINGS:
            for maxint in range(257):
                encoder = IntBaseEncoder(encoding, bits=maxint.bit_length(), signed=True)
                maxlen = len(encoder.encode(maxint))
                for i in range(-maxint, maxint + 1):
                    encoded = encoder.encode(i)
                    self.assertEqual(len(encoded), maxlen)
                    self.assertEqual(i, encoder.decode(encoded))


if __name__ == '__main__':
    unittest.main()
