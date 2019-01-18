import math
import time

from gitblobts.config import configure_logging
from gitblobts.store import Store

configure_logging()

if __name__ == '__main__':
    try:
        store = Store('/home/devuser/Documents/blobstoretest', compression=None or 'lzma',
                      key=None or b'JVGmuw3wRntCc7dcQHJ5q1noUs62ydR0Nw8HpyllKn8=')
        # store.addblob(b'asddf', '2345-12-21')
        # store.addblobs([b'a2010a', b'c2121c', b'b2020b'][0:], ['2010-10-12', '2121-12-21', '2020-03-03'][0:])
        print(list(store.getblobs('2100', -math.inf, pull=0)))
    except Exception:
        time.sleep(.01)  # Wait for logs to flush.
        raise
