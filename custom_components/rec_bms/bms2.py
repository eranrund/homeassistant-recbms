import asyncio
import logging
import crcmod 
import serial_asyncio
import struct

LOG = logging.getLogger(__name__)

crc16 = crcmod.mkCrcFun(0x18005, 0, True)

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


class BmsProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport = None
        self.recv_buf = bytes()
        
    def connection_made(self, transport):
        self.transport = transport
        LOG.error('port opened', transport)
        #transport.serial.rts = False  # You can manipulate Serial object via transport
        #transport.write(b'Hello, World!\n')  # Write serial data via transport

    def data_received(self, data):
        LOG.debug('data received', repr(data))
        self.recv_buf += data

    def connection_lost(self, exc):
        LOG.error('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')
        
        
    async def cmd(self, text, timeout=0.5):
        data = bytes([16, 0x00, len(text)]) + bytes(text, 'utf-8')
        crc = crc16(data)
        data = bytes([0x55]) + data + bytes([crc>>8, crc&0xff, 0xaa])
        self.transport.write(data)
        await asyncio.sleep(timeout) # Give the BMS time to respond
        
        buf = self.recv_buf
        self.recv_buf = bytes()
        
        
        #print(buf)
        #print(' '.join(hex(a) for a in buf))
        return self.__class__.decode(buf)
        
    async def retrying_cmd(self, text, timeout=0.5, tries=5):
        while True:
            try:
                return await self.cmd(text, timeout)
            except:
                LOG.exception(f"Error performing command {text}")

                tries -= 1
                if tries == 0:
                    return None
                await asyncio.sleep(1)
        
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
        
    async def identify(self):
        msgs = await self.retrying_cmd('*IDN?')
        return msgs[0].decode()
        
    async def cell_voltages(self):
        msgs = await self.retrying_cmd('CELL?')
        data = msgs[1]
        assert len(data) % 4 == 0, data
        vals = []
        for chunk in chunks(data, 4):
            vals.append(round(struct.unpack('<f', chunk)[0], 3))
        return vals
        

    async def cell_impedances(self):
        msgs = await self.retrying_cmd('RINT?')
        data = msgs[1]
        assert len(data) % 4 == 0, data
        vals = []
        for chunk in chunks(data, 4):
            vals.append(round(struct.unpack('<f', chunk)[0] * 1000, 3))
        return vals
        
    async def lcd1(self):
        msgs = await self.retrying_cmd('LCD1?')
        data = msgs[1]
        assert len(data) % 4 == 0, data
        vals = []
        for chunk in chunks(data, 4):
            vals.append(struct.unpack('<f', chunk)[0])
        return vals