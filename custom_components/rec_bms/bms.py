import asyncio
import logging
import crcmod 
import serial_asyncio
import struct

LOG = logging.getLogger(__name__)

crc16 = crcmod.mkCrcFun(0x18005, 0, True)

class Bms:
    def __init__(self, device):
        self.device = device
        self.connected = False

    async def connect(self):
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=self.device, baudrate=56000)
        self.connected = True

    def decode(buf):
        msgs = []
        state = 'WAIT_START'

        da = None
        sa = None
        n = None
        msg = []
        crc1 = None
        crc2 = None

        while len(buf):
            ch = buf[0]
            buf = buf[1:]
            #print(ch, buf, state)

            if state == 'WAIT_START':
                if ch == 0x55:
                    state = 'WAIT_DA'
            elif state == 'WAIT_DA':
                da = ch
                state = 'WAIT_SA'
            elif state == 'WAIT_SA':
                sa = ch
                state = 'WAIT_N'
            elif state == 'WAIT_N':
                n = ch
                state = 'READ_DATA'
            elif state == 'READ_DATA':
                msg.append(ch)
                if len(msg) == n:
                    state = 'CRC1'
            elif state == 'CRC1':
                crc1 = ch
                state = 'CRC2'
            elif state == 'CRC2':
                crc2 = ch
                state = 'WAIT_END'
            elif state == 'WAIT_END':
                if ch == 0xaa:
                    state = 'WAIT_START'
                    msgs.append(bytes(msg))
                    
                    da = None
                    sa = None
                    n = None
                    msg = []
                    crc1 = None
                    crc2 = None

        return msgs

    async def cmd(self, text, timeout=0.5):
        if not self.connected:
            await self.connect()

        data = bytes([16, 0x00, len(text)]) + bytes(text, 'utf-8')
        crc = crc16(data)
        data = bytes([0x55]) + data + bytes([crc>>8, crc&0xff, 0xaa])
        self.writer.write(data)
        await self.writer.drain()
        await asyncio.sleep(timeout) # Give the BMS time to respond
        buf = await self.reader.read(100)
        print(buf)
        print(' '.join(hex(a) for a in buf))
        return self.__class__.decode(buf)

    async def retrying_cmd(self, text, timeout=0.5, tries=5):
 
        while True:
            try:
                return await asyncio.wait_for(self.cmd(text, timeout), 1)
            except:
                LOG.exception(f"Error performing command {text}")
                self.connected = False
                self.reader = None
                self.writer = None

                tries -= 1
                if tries == 0:
                    raise

    async def identify(self):
        msgs = await self.retrying_cmd('*IDN?')
        return msgs[0].decode()




async def main():
    s = Bms("/dev/ttyUSB0")
    print(await s.identify())

if __name__ == '__main__':
    asyncio.run(main())
