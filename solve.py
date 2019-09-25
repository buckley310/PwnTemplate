#!/usr/bin/env python3

import os
import sys
import struct
import asyncio


###############################################################################


async def main():

    # ---- Interact with a subprocess
    r = await target().shell("/bin/sh")
    await r.ptyUpgrade()
    await r.writeline(b'PS1="\\u:\\w$ "')
    await r.interact(raw=True)

    # ---- interact with an incoming tcp connection, like netcat -l
    # r = await target().tcp_accept(port=8888, host='127.0.0.1')
    # await r.interact()

    # ---- connect to a TCP service and dump output
    # r = await target().tcp('towel.blinkenlights.nl', 23)
    # await r.cat()


###############################################################################


def p32(x, sign=False): return struct.pack('i' if sign else 'I', x)


def p64(x, sign=False): return struct.pack('q' if sign else 'Q', x)


def u32(x, sign=False): return struct.unpack('i' if sign else 'I', x)[0]


def u64(x, sign=False): return struct.unpack('q' if sign else 'Q', x)[0]


class target():
    def __init__(self):
        self._initialized = False

    def _bind_io(self):
        self.read = self.reader.read
        self.readline = self.reader.readline
        self.readexactly = self.reader.readexactly
        self.readuntil = self.reader.readuntil
        self.at_eof = self.reader.at_eof
        self.writer_is_closing = self.writer.is_closing
        self.close = self.writer.close

    async def tcp_accept(self, host=None, port=1337):
        async def tcp_recv_conn(reader, writer):
            self.reader, self.writer = reader, writer
            await tcp_accepted.put(True)
        assert not self._initialized
        self._initialized = True
        tcp_accepted = asyncio.Queue()
        async with await asyncio.start_server(tcp_recv_conn, host, port):
            await tcp_accepted.get()
        self._bind_io()
        return self

    async def tcp(self, addr, port):
        assert not self._initialized
        self._initialized = True
        self.reader, self.writer = (await asyncio.open_connection(addr, port))
        self._bind_io()
        return self

    async def shell(self, cmd):
        assert not self._initialized
        self._initialized = True
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE)
        self.reader, self.writer = proc.stdout, proc.stdin
        self._bind_io()
        return self

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def writeline(self, data):
        self.writer.write(data+b'\n')
        await self.writer.drain()

    async def cat(self, escape=False, verbose=False):
        if escape:
            while not self.at_eof():
                print(repr(await self.read(n=8192))[2:-1], end='', flush=True)
        else:
            while not self.at_eof():
                sys.stdout.buffer.write(await self.read(n=8192))
                sys.stdout.buffer.flush()
            os.system('stty sane')
        if verbose:
            print("\n\n-- RECEIVED EOF --\n")

    async def ptyUpgrade(self):
        await self.writeline(b'\n\n\n')
        await self.writeline(b";".join([
            b""" exec %s -c 'import pty; pty.spawn("/bin/sh")' """ % py
            for py in [b"python", b"python3", b"python2"]
        ]))
        await self.writeline(b'exec bash')

    async def interact(self, raw=False):
        async def send_keys():
            loop = asyncio.get_running_loop()
            while True:
                data = await loop.run_in_executor(None, sys.stdin.buffer.read1)
                if self.writer_is_closing():
                    break
                await self.write(data)
        if raw:
            os.system('stty -icanon -isig -echo')
        await asyncio.gather(send_keys(), self.cat(verbose=True))


asyncio.run(main())
