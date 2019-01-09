from gitblobts.config import configure_logging
from gitblobts.store import Store

configure_logging()

if __name__ == '__main__':
    import time
    store = Store('/home/devuser/Documents/blobdumptest', compression=None or 'bz2',
                  key=None or b'JVGmuw3wRntCc7dcQHJ5q1noUs62ydR0Nw8HpyllKn8=')
    print(store.addblobs([str(time.localtime()).encode()*3 for i in range(2)], ['5 minutes ago', 'now']))
    print(next(store.getblobs('now', '2 minutes ago', pull=0), None))
