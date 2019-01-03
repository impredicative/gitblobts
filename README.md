# gitblobts

`gitblobts` is a git-backed time-indexed blob storage package.
It stores a blob as a new file in a preexisting local git repo with a remote.
It then commits and pushes the file.
The file is assigned the a nanosecond UTC timestamp as its name.
The package allows subsequent retrieval of the blobs by a timestamp range.

The package does not support multi-user use.

## Installation
Using Python 3.7+, run `pip install gitblobts`.

## Usage

Storage:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
store.add('a string', timestamp='3 minutes ago')
store.add(b'some bytes')
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
