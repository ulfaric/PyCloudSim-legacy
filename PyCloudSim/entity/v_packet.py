from __future__ import annotations
from typing import List, Tuple, Union, Callable, Optional, TYPE_CHECKING
from random import randint, randbytes

import networkx as nx
from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity
from .v_physical_entity import PhysicalEntity

if TYPE_CHECKING:
    from .v_nic import vNIC
    from .v_request import vRequest
    from .v_router import vRouter
    from .v_switch import vSwitch
    from .v_host import vHost
    from .v_gateway import vGateway


class vPacket(VirtualEntity):
    def __init__(
        self,
        source: Union[vHost, vGateway],
        destination: Union[vHost, vGateway],
        size: int = 65536,
        request: Optional[vRequest] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vPacket

        Args:
            source (Union[vHost, vGateway]): the source of the vPacket.
            destination (Union[vHost, vGateway]): the destination of the vPacket.
            size (int, optional): the size of the vPacket in bytes. Defaults to 65536.
            request (Optional[vRequest], optional): the assoicated vRequest. Defaults to None.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.

        Raises:
            AttributeError: _description_
        """
        super().__init__(at, after, label)
        self._source = source
        self._destination = destination
        if source is destination:
            self._loopback = True
            self._path = [source]
            self._current_hop = self.path[0]
        else:
            path = nx.shortest_path(simulation.topology, source, destination)
            if len(path) != 0:
                self._path = path
                self._current_hop = path[0]
            else:
                raise AttributeError(
                    f"No path found between {source.__class__.__name__} {source.label} and {destination.__class__.__name__} {destination.label}"
                )
        self._request_id = request.id if request is not None else None
        self._nic_id = int()
        self._content = randbytes(size)
        self._size = len(self.content) * simulation.packet_size_amplifier
        self._on_creation = lambda: self.source.cache_packet(self)
        
    def creation(self):
        """The creation process of the vPacket."""
        if self.request:
            if self.request.failed:
                LOGGER.debug(f"{simulation.now:0.2f}:\tvPacket {self.label} creation cancelled due to vRequest {self.request.label} failed.")
                return
        simulation.PACKETS.append(self)
        return super().creation()

    def termination(self):
        """The termination process of the vPacket."""
        super().termination()
        if self.completed:
            # release the ram of the current hop
            if self.current_hop.__class__.__name__ != "vGateway":
                self.current_hop.ram.release(self)
            self.current_hop.packets.remove(self)
        if self.dropped:
            # fail the associated request
            if self.request is not None:
                self.request.fail()

    def complete(self):
        """Complete the vPacket."""
        if not self.completed:
            if self.request is not None:
                if not self.request.failed:
                    self.status.append(COMPLETED)
            else:
                self.status.append(COMPLETED)
            self.terminate()
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvPacket {self.label} reached destination {self.current_hop.__class__.__name__} {self.current_hop.label}."
            )

    def drop(self):
        """Drop the vPacket."""
        if not self.dropped:
            self.status.append(DROPPED)
            self.terminate()

    @property
    def source(self) -> Union[vHost, vGateway]:
        """Return the source of the vPacket."""
        return self._source

    @property
    def destination(self) -> Union[vHost, vGateway]:
        """Return the destination of the vPacket."""
        return self._destination

    @property
    def path(self) -> List[PhysicalEntity]:
        """Return the path of the vPacket."""
        return self._path  # type: ignore

    @property
    def content(self) -> bytes:
        """The content of the vPacket."""
        return self._content

    @property
    def size(self) -> int:
        """The size of the vPacket in bytes."""
        return self._size

    @property
    def loopback(self) -> bool:
        """return true if the source and destination is on the same host."""
        return self._loopback

    @property
    def request_id(self) -> Optional[int]:
        """The id of the associated vRequest."""
        return self._request_id

    @property
    def request(self) -> Optional[vRequest]:
        """The associated vRequest."""
        if self.request_id is None:
            return None
        else:
            for request in simulation.REQUESTS:
                if request.id == self.request_id:
                    return request
            raise RuntimeError(
                f"vPacket {self.label} can not find its associated request."
            )

    @property
    def current_hop(self) -> Union[vHost, vRouter, vSwitch, vGateway]:
        """The current hop of the vPacket."""
        return self._current_hop  # type: ignore

    @property
    def next_hop(self) -> Union[vHost, vRouter, vSwitch, vGateway]:
        """The next hop of the vPacket."""
        if self.current_hop == self.destination:
            return self.destination
        else:
            return self.path[self.path.index(self.current_hop) + 1]  # type: ignore

    @property
    def nic_id(self) -> int:
        """The id of the associated vNIC."""
        return self._nic_id

    @property
    def nic(self) -> vNIC:
        """The associated vNIC."""
        for nic in simulation.NICS:
            if nic.id == self.nic_id:
                return nic
        raise RuntimeError(f"vPacket {self.label} can not find its associated NIC.")

    @property
    def transmitting(self) -> bool:
        """Return true if the vPacket is transmitting."""
        return TRANSMITTING in self.status

    @property
    def priority(self) -> int:
        """Return the priority of the vPacket."""
        if self.request is None:
            return 0
        else:
            return self.request.priority

    @property
    def dropped(self) -> bool:
        """Return true if the vPacket is dropped."""
        return DROPPED in self.status

    @property
    def queued(self) -> bool:
        """Return true if the vPacket is queued."""
        return QUEUED in self.status

    @property
    def decoded(self) -> bool:
        """Return true if the vPacket is decoded."""
        return DECODED in self.status
