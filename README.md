# gitblobts

`gitblobts` is a Python package for git-backed time-indexed blob storage.
Even so, a lock-in of the stored files with git is avoided.

Its goal is to ensure data availability both locally and remotely.
It stores each blob as a file in a preexisting local git repo.
The name of the file is a high-resolution nanosecond UTC timestamp.
It then commits and pushes the changes.
Given the pull and push actions, collaborative use of the same remote repo is supported.

Subsequent retrieval of the blobs is by a UTC time range.

An effort has been made to keep third-party package requirements to a minimum.
This is in order to lower any risk of long-term compatibility and maintainability issues.
As the code is in an early stage, the implementation should be reviewed before use.

## Installation
Using Python 3.7+, run `pip install gitblobts`. Any older version of Python will not work.

## Usage

Storage:
```python
from typing import List
import gitblobts, json, time, urllib

store = gitblobts.Store('/path_to/preexisting_git_repo')

filename1_as_time_utc_ns: int = store.addblob(blob='a byte encoded string'.encode())
filename2_as_time_utc_ns: int = store.addblob(blob=b'some bytes' * 1000, time_utc=time.time())
filename3_as_time_utc_ns: int = store.addblob(blob=json.dumps([0, 1., 2.2, 3]).encode(), time_utc=time.time())
filename4_as_time_utc_ns: int = store.addblob(blob=urllib.request.urlopen('https://i.imgur.com/3GmPd7O.png').read())

filenames1_as_time_utc_ns: List[int] = store.addblobs(blobs=[b'first blob', b'another blob'])
filenames2_as_time_utc_ns: List[int] = store.addblobs(blobs=[b'A', b'B'], times_utc=[time.time(), time.time()])
```

Retrieval:
```python
from typing import List
from gitblobts import Blob, Store
import time

store = Store('/path_to/preexisting_git_repo')

blobs: List[Blob] = list(store.getblobs())
blobs_bytes: List[bytes] = [b.blob for b in blobs]
times_utc_ns: List[int] = [b.time_utc_ns for b in blobs]

blobs2_ascending: List[Blob] = list(store.getblobs(start_utc='since midnight', end_utc='now'))
blobs2_descending: List[Blob] = list(store.getblobs(start_utc='now', end_utc='since midnight'))
blobs3_ascending: List[Blob] = list(store.getblobs(start_utc=time.time() - 86400, end_utc=time.time()))
blobs3_descending: List[Blob] = list(store.getblobs(start_utc=time.time(), end_utc=time.time() - 86400))
```

## To do
* Add logging.
* Perform compression.
* Support encryption after compression.
* Considering organizing blobs into directory structure: YYYY/MM/DD/HH
* Support asyncio or avoiding waiting for commit+push.
* Support label/key/name/hash as filenames as an alternative to timestamp.
