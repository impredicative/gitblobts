# gitblobts

`gitblobts` is a Python package for git-backed time-indexed blob storage.
Its goal is to ensure data availability both locally and remotely.
It stores each blob as a file in a preexisting local git repo.
The name of the file is a high-resolution timestamp.
It then commits and pushes the changes.
The file is assigned a nanosecond UTC timestamp as its name.
The package allows subsequent retrieval of the blobs by a UTC time range.
Collaborative use of the same remote repo is supported.

## Installation
Using Python 3.7+, run `pip install gitblobts`. Any older version of Python will not work.

## Usage

Storage:
```python
from typing import List
import gitblobts, json, time, urllib

store = gitblobts.Store('/path_to/preexisting_git_repo')

filename1_as_time_utc_ns: int = store.writeblob(blob='a byte encoded string'.encode())
filename2_as_time_utc_ns: int = store.writeblob(blob=b'some bytes', time_utc=time.time())
filename3_as_time_utc_ns: int = store.writeblob(blob=json.dumps([0, 1., 2.2, 3]).encode(), time_utc=time.time())
filename4_as_time_utc_ns: int = store.writeblob(blob=urllib.request.urlopen('https://i.imgur.com/3GmPd7O.png').read())

filenames1_as_time_utc_ns: List[int] = store.writeblobs(blobs=[b'first blob', b'another blob'])
filenames2_as_time_utc_ns: List[int] = store.writeblobs(blobs=[b'A', b'B'], times_utc=[time.time(), time.time()])
```

Retrieval:
```python
from typing import List
from gitblobts import Blob, Store
import time

store = Store('/path_to/preexisting_git_repo')

blobs1: List[Blob] = list(store.readblobs())
blobs_bytes: List[bytes] = [b.blob for b in blobs1]
times_utc_ns: List[int] = [b.time_utc_ns for b in blobs1]

blobs2: List[Blob] = list(store.readblobs(start_utc='since midnight', end_utc='now'))
blobs3: List[Blob] = list(store.readblobs(start_utc=time.time() - 86400, end_utc=time.time()))
blobs4: List[Blob] = list(store.readblobs(start_utc=time.time(), end_utc=time.time() - 86400))
```

## To do
* Perform compression.
* Organize blobs into directory structure: YYYY/MM/DD/HH
* Support encryption.
* Support asyncio or avoiding waiting for commit+push.
* Support label/key/name/hash as filenames as an alternative to timestamp.
