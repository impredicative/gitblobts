from gitblobts.config import configure_logging
from gitblobts.store import Store

configure_logging()

if __name__ == '__main__':
    store = Store('/home/devuser/Documents/blobdumptest', compression='gzip')
    print(store.addblobs([str(i+5).encode()*111 for i in range(2)], ['now', 'now']))
    print(next(store.getblobs('now', 'yesterday', pull=0), None))
