# gitblobts

`gitblobts` is an experimental Python package for git-backed time-indexed blob storage.
Even so, a lock-in of the stored files with git is avoided.

Its goal is to ensure availability of data both locally and remotely.
It stores each blob as a file in a preexisting local and remote git repository.
The name of the file is a high-resolution nanosecond UTC timestamp.
Given the pull and push actions of git, collaborative use of the same remote repo is supported.

Subsequent retrieval of the blobs is by a UTC time range.
At this time there is no implemented method to remove or overwrite a blob; this is by design.
From the perspective of the package, once a blob is written, it is considered read-only.
If an attempt is made to write a blob with the same timestamp as a preexisting blob, the supplied timestamp will be
incremented, and a new blob will be written to a new file.

An effort has been made to keep third-party package requirements to a minimum.
As the code is in an early stage, the implementation should be reviewed before use.

## Installation
Using Python 3.7+, run `pip install gitblobts` (pending). Older version of Python will not work.
This is due to a reliance on [`time_ns`](https://docs.python.org/3/library/time.html#time.time_ns).
This function doesn't exist in older versions.

## Usage

### Storage
```python
from typing import List, Optional
import gitblobts, json, time, urllib.request

optional_compression_module_name: Optional[str] = [None, 'bz2', 'gzip', 'lzma'][2]
optional_user_saved_encryption_key: Optional[bytes] = [None, gitblobts.generate_key()][1]
store = gitblobts.Store('/path_to/preexisting_git_repo', compression=optional_compression_module_name,
                        key=optional_user_saved_encryption_key)

filename1_as_time_utc_ns: int = store.addblob(blob='a byte encoded string'.encode())
filename2_as_time_utc_ns: int = store.addblob(blob=b'some bytes' * 1000, time_utc=time.time())
filename3_as_time_utc_ns: int = store.addblob(blob=json.dumps([0, 1., 2.2, 3]).encode(), time_utc=time.time())
filename4_as_time_utc_ns: int = store.addblob(blob=urllib.request.urlopen('https://i.imgur.com/3GmPd7O.png').read())

filenames1_as_time_utc_ns: List[int] = store.addblobs(blobs=[b'first blob', b'another blob'])
filenames2_as_time_utc_ns: List[int] = store.addblobs(blobs=[b'A', b'B'], times_utc=[time.time(), time.time()])
```

### Retrieval
```python
from typing import List
from gitblobts import Blob, Store
import time

store = Store('/path_to/preexisting_git_repo', compression='gzip', key=b'JVGmuw3wRntCc7dcQHJ5q1noUs62ydR0Nw8HpyllKn8=')

blobs: List[Blob] = list(store.getblobs())
blobs_bytes: List[bytes] = [b.blob for b in blobs]
times_utc_ns: List[int] = [b.time_utc_ns for b in blobs]

blobs2_ascending: List[Blob] = list(store.getblobs(start_utc='midnight yesterday', end_utc='now'))
blobs2_descending: List[Blob] = list(store.getblobs(start_utc='now', end_utc='midnight yesterday', pull=True))
blobs3_ascending: List[Blob] = list(store.getblobs(start_utc=time.time() - 86400, end_utc=time.time(), pull=True))
blobs3_descending: List[Blob] = list(store.getblobs(start_utc=time.time(), end_utc=time.time() - 86400))
```

## To do
* Publish to pypi.
* Add tests, also refactoring the code to be more testable.
* Add documentation.

<!--
## Wish list
* Considering organizing blobs into directory structure: YYYY/MM/DD/HH
* Support asyncio or avoiding waiting for commit+push.
* Support label/key/name/hash as filenames as an alternative to timestamp.
* Support sharding across multiple repos.
-->