from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import logging
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RECBMSError(Exception):
    pass


from .bms2 import BmsProtocol
import serial_asyncio


class RECBMSDataUpdateCoordinator(DataUpdateCoordinator[BmsProtocol]):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
    ) -> None:
        _LOGGER.info("coordinator init")
        self.serial_port = entry.data["serial_port"]
        self.unsub: CALLBACK_TYPE | None = None
        self.recbms = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )

    @callback
    def _start(self):
        async def task():
            transport, protocol = await serial_asyncio.create_serial_connection(asyncio.get_event_loop(), BmsProtocol, '/dev/ttyUSB0', baudrate=56000)
            while protocol.transport is None:
                _LOGGER.error("Waiting for transport...")
                await asyncio.sleep(1)

            while True:
                _LOGGER.error("coordinator task BMS start ----")

                data = {}

                for i in range(3):
                    try:
                        data["cell_voltages"] = await protocol.cell_voltages()
                    except:
                        _LOGGER.exception("cell_voltages failed")
                        await asyncio.sleep(1)
                    else:
                        break

                for i in range(3):
                    try:
                        data["cell_impedances"] = await protocol.cell_impedances()
                    except:
                        _LOGGER.exception("cell_impedances failed")
                        await asyncio.sleep(1)
                    else:
                        break

                for i in range(3):
                    try:
                        (min_cell_v, max_cell_v, current, max_temp, pack_v, soc, soh) = await protocol.lcd1()
                        data["min_cell_v"] = round(min_cell_v, 3)
                        data["max_cell_v"] = round(max_cell_v, 3)
                        data["current"] = round(current, 3)
                        data["max_temp"] = round(max_temp, 3)
                        data["pack_v"] = round(pack_v, 3)
                        data["soc"] = round(soc, 3) * 100.0
                        data["soh"] = round(soh, 3) * 100.0
                    except:
                        _LOGGER.exception("lcd1 failed")
                        await asyncio.sleep(1)
                    else:
                        break


                _LOGGER.info("data: "+ repr(data))
                self.async_set_updated_data(data)

                await asyncio.sleep(10)

        async def close(self):
            # TODO - this does nothing
            self.unsub = None
            self.recbms = None

        # Shutdown on Home Assistant shutdown
        self.unsub = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, close
        )

        # Start listening
        self.config_entry.async_create_background_task(
            self.hass, task(), "recbms-loop"
        )



    # @callback
    # def _use_websocket(self):
    #     async def listen():
    #         """Listen for state changes via WebSocket."""
    #         try:
    #             await self.recbms.listen(callback=self.async_set_updated_data)
    #         except RECBMSConnectionClosedError as err:
    #             self.last_update_success = False
    #             self.logger.info(err)
    #         except RECBMSError as err:
    #             self.last_update_success = False
    #             self.async_update_listeners()
    #             self.logger.error(err)

    #         # Ensure we are disconnected
    #         await self.recbms.disconnect()
    #         if self.unsub:
    #             self.unsub()
    #             self.unsub = None

    #     async def close_websocket(_: Event) -> None:
    #         """Close WebSocket connection."""
    #         self.unsub = None
    #         await self.recbms.disconnect()

    #     # Clean disconnect WebSocket on Home Assistant shutdown
    #     self.unsub = self.hass.bus.async_listen_once(
    #         EVENT_HOMEASSISTANT_STOP, close_websocket
    #     )

    #     # Start listening
    #     self.config_entry.async_create_background_task(
    #         self.hass, listen(), "wled-listen"
    #     )

    async def _async_update_data(self):
        _LOGGER.info("coordinator _async_update_data")

        if not self.unsub:
           self._start()
