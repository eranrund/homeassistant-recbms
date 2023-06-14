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


from .bms import Bms


class RECBMSDataUpdateCoordinator(DataUpdateCoordinator[Bms]):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
    ) -> None:
        _LOGGER.info("coordinator init")
        self.serial_port = entry.data["serial_port"]
        self.unsub: CALLBACK_TYPE | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )

    @callback
    def _start(self):
        async def task():
            while self.serial_port != None:
                _LOGGER.error("coordinator task BMS")
                recbms = Bms(self.serial_port)

                try:
                    cell_voltages = await recbms.cell_voltages()
                except:
                    self.logger.exception("cell_voltages failed")
                    cell_voltages = None

                recbms = None

                _LOGGER.error("cell_voltages: "+ repr(cell_voltages))
                self.async_set_updated_data({
                    "cell_voltages": cell_voltages,
                })

                await asyncio.sleep(1)

        async def close(self):
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
