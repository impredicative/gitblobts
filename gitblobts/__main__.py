import time

from gitblobts.config import configure_logging
from gitblobts.store import Store

configure_logging()

if __name__ == '__main__':
    try:
        store = Store('/home/devuser/Documents/blobstoretest', compression=None or 'bz2',
                      key=None or b'JVGmuw3wRntCc7dcQHJ5q1noUs62ydR0Nw8HpyllKn8=')
        # print(store.addblobs([b'a2010a', b'c2121c', b'b2020b', b'd4567d'][0:], ['2010', '2121', '2020', '4567'][0:]))
        # print(list(store.getblobs('1900', '8000', pull=0)))
    except Exception:
        time.sleep(.01)  # Wait for logs to flush.
        raise
