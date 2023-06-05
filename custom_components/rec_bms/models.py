"""Models for RECBMS."""
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RECBMSDataUpdateCoordinator


class RECBMSEntity(CoordinatorEntity[RECBMSDataUpdateCoordinator]):
    """Defines a base RECBMS entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this RECBMS device."""
        return DeviceInfo(
            connections={
                #(CONNECTION_NETWORK_MAC, self.coordinator.data.info.mac_address)
            },
            #identifiers={(DOMAIN, self.coordinator.data.info.mac_address)},
            # name=self.coordinator.data.info.name,
            # manufacturer=self.coordinator.data.info.brand,
            # model=self.coordinator.data.info.product,
            # sw_version=str(self.coordinator.data.info.version),
            # hw_version=self.coordinator.data.info.architecture,
            # configuration_url=f"http://{self.coordinator.wled.host}",
            hmm="TODO",
        )
