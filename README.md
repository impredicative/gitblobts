# gitblobts

`gitblobts` is a Python package for git-backed time-indexed blob storage.
Its goal is to ensure data availability both locally and remotely.
It stores each blob as a file in a preexisting local git repo.
It then commits and pushes the changes.
The file is assigned a nanosecond UTC timestamp as its name.
The package allows subsequent retrieval of the blobs by a UTC time range.
Collaborative use of the same remote repo is supported.

## Installation
Using Python 3.7+, run `pip install gitblobts`. Any older version of Python will not work.

## Usage

Storage:
```python
import gitblobts, json, time, urllib

store = gitblobts.Store('/path_to/preexisting_git_repo')
store.writeblob(blob='a byte encoded string'.encode())
store.writeblob(blob=json.dumps([0, 1., 2.2, 3]).encode(), time_utc=time.time())
store.writeblob(blob=b'some bytes', time_utc=time.gmtime())
store.writeblob(blob=urllib.request.urlopen('https://upload.wikimedia.org/wikipedia/en/a/a9/Example.jpg').read())
```

Retrieval:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
blobs = list(store.readblobs(start='1 week ago', end='now'))
```

## To do
* Perform compression.
* Organize blobs into directory structure: YYYY/MM/DD/HH
* Support encryption.
* Support asyncio or avoiding waiting for commit+push.
