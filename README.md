# gitblobts

`gitblobts` stores a blob as a new file in a preexisting local git repo with a remote.
It then commits and pushes the file.
The file is assigned the current nanosecond UTC timestamp as its name.
The package allows subsequent retrieval of the blobs by a timestamp range.

The package is currently intended for single-threaded single-user use.

## Installation
`pip install gitblobts`

## Usage

Storage:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
store.add('any blob')
store.add('another blob')
```

Retrieval:
```python
import gitblobts

store = gitblobts.Store('/path_to/preexisting_git_repo')
blobs = store.get(start='1 week ago', end='now', tz='localtime')
```

## To do
* Support batching commit+push.
* Support compression.
* Support encryption.
* Support asyncio or avoiding waiting for commit+push.
