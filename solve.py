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
    await r.write(b'PS1="\\u:\\w$ "\n')
    await r.interact(raw=True)

    # ---- interact with an incoming tcp connection, like netcat -l
    # r = await target().tcp_accept(port=8888, host='127.0.0.1')
    # await r.interact()

    # ---- connect to a TCP service and dump output
    # r = await target().tcp('towel.blinkenlights.nl', 23)
    # await r.cat()


###############################################################################


def p32u(x): return struct.pack('I', x)


def p32s(x): return struct.pack('i', x)


def p64u(x): return struct.pack('Q', x)


def p64s(x): return struct.pack('q', x)


def u32u(x): return struct.unpack('I', x)[0]


def u32s(x): return struct.unpack('i', x)[0]


def u64u(x): return struct.unpack('Q', x)[0]


def u64s(x): return struct.unpack('q', x)[0]


class target():
    def __init__(self):
        self.initialized = False

    async def tcp_accept(self, host=None, port=1337):
        async def tcp_recv_conn(reader, writer):
            self.reader, self.writer = reader, writer
            await tcp_accepted.put(True)
        assert not self.initialized
        self.initialized = True
        tcp_accepted = asyncio.Queue()
        async with await asyncio.start_server(tcp_recv_conn, host, port):
            await tcp_accepted.get()
        return self

    async def tcp(self, addr, port):
        assert not self.initialized
        self.initialized = True
        self.reader, self.writer = (await asyncio.open_connection(addr, port))
        return self

    async def shell(self, cmd):
        assert not self.initialized
        self.initialized = True
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE)
        self.reader, self.writer = proc.stdout, proc.stdin
        return self

    async def readuntil(self, key):
        data = b''
        while not key in data:
            data += await self.reader.readexactly(1)
        return data

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def read(self, size=-1):
        if size >= 0:
            return await self.reader.readexactly(size)
        else:
            return await self.reader.read(8192)

    async def cat(self):
        while not self.reader.at_eof():
            sys.stdout.buffer.write(await self.read())
            sys.stdout.buffer.flush()
        os.system('stty sane')
        print("\n\n-- RECEIVED EOF --\n")

    async def ptyUpgrade(self):
        await self.write(b'\n\n\n')
        await self.write(b";".join([
            b""" exec %s -c 'import pty; pty.spawn("/bin/sh")' """ % py
            for py in [b"python", b"python3", b"python2"]
        ]))
        await self.write(b'\nexec bash\n')

    async def interact(self, raw=False):
        async def send_keys():
            loop = asyncio.get_running_loop()
            while True:
                data = await loop.run_in_executor(None, sys.stdin.buffer.read1)
                if self.writer.is_closing():
                    break
                await self.write(data)
        if raw:
            os.system('stty -icanon -isig -echo')
        await asyncio.gather(send_keys(), self.cat())


asyncio.run(main())
