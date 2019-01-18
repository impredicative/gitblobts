# gitblobts

`gitblobts` is an experimental Python package for **git-backed time-indexed blob storage**.
Even so, a lock-in of the stored files with git is avoided.
If encryption is not enabled, a lock-in of the file contents with this application is also avoided.

Its goal is to ensure availability of data both locally and remotely.
It stores each blob as a file in a preexisting local and remote git repository.
Each filename contains an encoded nanosecond timestamp and format version number.

Given the pull and push actions of git, collaborative use of the same remote repo is supported.
To prevent merge conflicts, there is a one-to-many mapping of timestamp to filenames.
This is accomplished by including sufficient random bytes in the filename to ensure uniqueness.

Subsequent retrieval of blobs is by a time range.
At this time there is no implemented method to remove or overwrite a blob; this is by design.
From the perspective of the package, once a blob is written, it is considered read-only.
An attempt to add a blob with the same timestamp as a preexisting blob will result in a new blob.

An effort has been made to keep third-party package requirements to a minimum.

## Links
* Code: [https://github.com/impredicative/gitblobts/](https://github.com/impredicative/gitblobts/)
* Docs: [https://gitblobts.readthedocs.io/](https://gitblobts.readthedocs.io/)
* Release: [https://pypi.org/project/gitblobts/](https://pypi.org/project/gitblobts/)

## Installation
Using Python 3.7+, install the package from PyPI: `pip install -U gitblobts`.

## Usage examples

### Storage
```python
from typing import Optional
import datetime, gitblobts, json, time, urllib.request

optional_compression_module_name: Optional[str] = [None, 'bz2', 'gzip', 'lzma'][2]
optional_user_saved_encryption_key: Optional[bytes] = [None, gitblobts.generate_key()][1]
store = gitblobts.Store('/path_to/preexisting_git_repo',
                        compression=optional_compression_module_name, key=optional_user_saved_encryption_key)

store.addblob('a byte encoded string'.encode())
store.addblob(b'some bytes' * 1000, timestamp=time.time())
store.addblob(blob=json.dumps([0, 1., 2.2, 3]).encode(),
              timestamp=datetime.datetime.now(datetime.timezone.utc).timestamp())
store.addblob(blob=urllib.request.urlopen('https://i.imgur.com/3GmPd7O.png').read())

store.addblobs(blobs=[b'first blob', b'another blob'])
store.addblobs(blobs=[b'A', b'B'], timestamps=[time.time(), time.time()])
```

### Retrieval
```python
from typing import List
from gitblobts import Blob, Store
import time

store = Store('/path_to/preexisting_git_repo', compression='gzip', key=b'JVGmuw3wRntCc7dcQHJ5q1noUs62ydR0Nw8HpyllKn8=')

blobs: List[Blob] = list(store.getblobs(pull=False))
blobs_bytes: List[bytes] = [b.blob for b in blobs]
timestamps: List[float] = [b.timestamp for b in blobs]

blobs2_ascending: List[Blob] = list(store.getblobs(start_time='midnight yesterday', end_time='now'))
blobs2_descending: List[Blob] = list(store.getblobs(start_time='now', end_time='midnight yesterday', pull=True))
blobs3_ascending: List[Blob] = list(store.getblobs(start_time=time.time() - 86400, end_time=time.time(), pull=True))
blobs3_descending: List[Blob] = list(store.getblobs(start_time=time.time(), end_time=time.time() - 86400))
```

<!--
## Wish list
* Add tests, also refactoring the code to be more testable.
* Considering organizing blobs into directory structure: YYYY/MM/DD/HH
* Support asyncio or avoiding waiting for commit+push.
* Support label/key/name/hash as filenames as an alternative to timestamp.
* Support sharding across multiple repos.
-->