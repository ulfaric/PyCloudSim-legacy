from __future__ import annotations
from random import choice
from typing import List, Optional, Union, Callable, TYPE_CHECKING
from ipaddress import IPv4Network, IPv4Address

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_physical_entity import PhysicalEntity

if TYPE_CHECKING:
    from .v_packet import vPacket


class vGateway(PhysicalEntity):
    def __init__(
        self,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a virtual gateway, which is the entry/exit point of the simulated cluster.

        Args:
            at (Union[int, float, Callable], optional): same as the entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as the entity. Defaults to None.
            label (Optional[str], optional): same as the entity. Defaults to None.
        """
        super().__init__(
            num_cpu_cores=1,
            ipc=1,
            frequency=1000,
            ram=1,
            rom=1,
            delay=0.01,
            at=at,
            after=after,
            label=label,
        )

    def creation(self):
        """Creation process of the virtual gateway."""
        return super().creation()

    def termination(self):
        """Termination process of the virtual gateway."""
        return super().termination()

    def _power_on(self):
        """Power on the virtual gateway."""
        super()._power_on()

    def _power_off(self):
        """Power off the virtual gateway."""
        super()._power_off()

    def cache_packet(self, packet: vPacket):
        """Cache a packet in the virtual gateway, no packet handler vProcess will be created."""
        self.packets.append(packet)
        if not packet.scheduled:
            packet.status.append(SCHEDULED)
            packet._scheduled_at = simulation.now
        packet.status.append(QUEUED)
        packet.status.append(DECODED)
        packet._current_hop = self
        if packet.path[-1] is self:
            packet.complete()
        self.send_packets()
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} cached packet {packet.label}."
        )
