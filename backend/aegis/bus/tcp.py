"""JSON Lines over TCP: one envelope per line, UTF-8, `\n` terminated."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

# Transport buffer, not a mission limit: the longest line we accept. A full
# backlog.batch (event_buffer.batch_size envelopes) must fit.
MAX_LINE_BYTES = 16 * 1024 * 1024


class LineTooLong(Exception):
    pass


async def connect(
    host: str, port: int
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    return await asyncio.open_connection(host, port, limit=MAX_LINE_BYTES)


async def serve(
    host: str,
    port: int,
    on_connect: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]],
) -> asyncio.Server:
    return await asyncio.start_server(on_connect, host, port, limit=MAX_LINE_BYTES)


async def read_line(reader: asyncio.StreamReader) -> str | None:
    """The next line without its newline, or None at end of stream."""
    try:
        data = await reader.readuntil(b"\n")
    except asyncio.IncompleteReadError as exc:
        if not exc.partial:
            return None
        data = exc.partial  # last line without a newline
    except asyncio.LimitOverrunError as exc:
        raise LineTooLong(f"line longer than {MAX_LINE_BYTES} bytes") from exc
    return data.decode("utf-8", errors="replace").rstrip("\r\n")


async def write_line(writer: asyncio.StreamWriter, line: str) -> None:
    writer.write(line.encode("utf-8") + b"\n")
    await writer.drain()


async def close(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await writer.wait_closed()
    except (ConnectionError, OSError):
        pass
