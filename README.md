# gitblobts

`gitblobts` is a git-backed time-indexed blob storage package.
It stores a blob as a new file in a preexisting local git repo.
It then commits and pushes the change.
The file is assigned a nanosecond UTC timestamp as its name.
The package allows subsequent retrieval of the blobs by a timestamp range.

The philosophy behind the package is that data must automatically be backed up elsewhere to guard against local data
loss, while also remaining available locally.

The package currently does not support any multi-user use.

## Installation
Using Python 3.7+, run `pip install gitblobts`.

## Usage

Storage:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
store.add('a byte encoded string'.encode(), timestamp='3 minutes ago')
store.add(b'some bytes')

import urllib
blob = urllib.request.urlopen('https://upload.wikimedia.org/wikipedia/en/a/a9/Example.jpg').read()
store.add(blob)
```

Retrieval:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
blobs = list(store.get(start='1 week ago', end='now'))
```

## To do
* Support batching new blobs before commit+push.
* Support compression.
* Support encryption.
* Support asyncio or avoiding waiting for commit+push.
