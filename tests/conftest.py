"""Shared pytest fixtures and compatibility shims."""

import inspect
from unittest.mock import Mock

import aiohttp

# aiohttp 3.14 added a required keyword-only ``stream_writer`` argument to
# ``ClientResponse.__init__``. aioresponses 0.7.9 does not pass it yet
# (https://github.com/pnuckowski/aioresponses/pull/288 is still open), so
# every mocked response raises a TypeError. aiohttp only reads
# ``stream_writer.output_size``, so a lightweight default is enough. Remove
# this shim once aioresponses ships a fix for aiohttp 3.14+.
_client_response_init = aiohttp.ClientResponse.__init__
_stream_writer_param = inspect.signature(_client_response_init).parameters.get(
    "stream_writer"
)
if _stream_writer_param is not None and _stream_writer_param.default is inspect.Parameter.empty:

    def _patched_init(self, *args, **kwargs):
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        _client_response_init(self, *args, **kwargs)

    aiohttp.ClientResponse.__init__ = _patched_init
