# ytpa-api-utils

## Description

This package contains utility functions used by the YouTube video predictive analytics (YTPA) system's API engine.
They support functionality for:
- requests: `request_utils.py`
- websockets: `websocket_utils.py`
- other: `misc_utils.py`

The file `websocket_utils.py` implements the send/receive logic for chunking a large pandas DataFrame, 
sending the chunks through a websocket connection, and assembling them into a single DataFrame on the other side. 
This allows for streaming DataFrames in a dynamic way while minimizing bandwidth per unit time.
It hides the websocket logic from both sides of the transaction, making it possible to set up the websocket
connection once and then deal only with DataFrame generators.


## Installation

Install from PyPI with `pip install ytpa-api-utils`.

## Make commands

Several make commands are implemented in `Makefile`.

### Testing

Tests are implemented in the `test/` directory, one file per module. Run them locally with `make test`.

### Deploying a new package version

A new version of the package can be deployed by incrementing the version number in `pyproject.toml` and running 
`make deploy`. 
A better practice is to `git push` and allow the Github Actions pipeline to take care of running tests and deploying 
the new version only when the entire pipeline succeeds.
Make sure to use the right version of the package in your other environments (update it in a requirements file and 
update the environment).
