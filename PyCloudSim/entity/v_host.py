from __future__ import annotations
from typing import List, Union, TYPE_CHECKING, Optional, Callable
import random

from Akatosh import Resource, Actor
from bitmath import GiB

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_physical_entity import PhysicalEntity
from .v_cpu import vCPU
from .v_nic import vNIC
from .v_process import vPacketHandler

if TYPE_CHECKING:
    from .v_container import vContainer
    from .v_volume import vVolume
    from .v_process import vProcess
    from .v_packet import vPacket
    from .v_switch import vSwitch


class vHost(PhysicalEntity):
    def __init__(
        self,
        num_cpu_cores: int,
        ipc: Union[int, float],
        frequency: Union[int, float],
        ram: int,
        rom: int,
        delay: float = 0.01,
        taint: Optional[str] = None,
        switch: Optional[vSwitch] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Creat a virtual host.

        Args:
            num_cpu_cores (int): number of cpu cores.
            ipc (Union[int, float]): the instructions per cycle of the CPU.
            frequency (Union[int, float]): the frequency of the CPU.
            ram (int): the size of the RAM in MiB.
            rom (int): the size of the ROM in GiB.
            delay (float, optional): the packet processing delay. Defaults to 0.01.
            taint (Optional[str], optional): the taint of this vHost, used during container scheduling. Defaults to None.
            switch (Optional[vSwitch], optional): the switch this vHost is connected with. Defaults to None.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(
            num_cpu_cores=num_cpu_cores,
            ipc=ipc,
            frequency=frequency,
            ram=ram,
            rom=rom,
            delay=delay,
            at=at,
            after=after,
            label=label,
        )
        self._cpu_reservor = Resource(
            capacity=(num_cpu_cores * 1000),
            label=f"{self.__class__.__name__} {self.label} CPU reservor",
        )
        self._ram_reservor = Resource(
            capacity=(ram * 1024),
            label=f"{self.__class__.__name__} {self.label} RAM reservor",
        )
        self._taint = taint or str()
        self._containers = list()
        self._volumes = list()
        self._privisioned = False
        self._delay = delay
        simulation.HOSTS.append(self)
        simulation.topology.add_node(self)
        if switch is not None:
            switch.connect_device(self)
        else:
            simulation.core_switch.connect_device(self)

    def creation(self):
        """The creation process of the vHost.
        """
        super().creation()
        simulation.core_switch.connect_device(self)

    def termination(self):
        """The termination process of the vHost.
        """
        return super().termination()

    def _power_on(self):
        """Power on the vHost."""
        super()._power_on()
        self.cpu.power_on()
        for interface in self.interfaces:
            interface.power_on()

    def _power_off(self):
        """Power off the vHost."""
        super()._power_off()
        self.cpu.power_off()
        for interface in self.interfaces:
            interface.power_off()

    def allocate_container(self, container: vContainer):
        """Allocate a container on the vHost."""
        self.containers.append(container)
        self.cpu_reservor.distribute(container, container.cpu_request)
        self.ram_reservor.distribute(container, container.ram_request)
        self.rom.distribute(container, container.image_size)
        container._host_id = self.id
        container.status.append(SCHEDULED)
        LOGGER.info(
            f"{simulation.now:0.2f}:\tvContainer {container.label} is scheduled on vHost {self.label}."
        )
        container.init_deamon()
        container.microservice.evaluate()
        simulation.request_scheduler.schedule()

    def allocate_volume(self, volume: vVolume):
        """Allocate a volume on the vHost."""
        self.rom.distribute(volume, volume.size)
        self.volumes.append(volume)
        volume._host_id = self.id
        LOGGER.info(
            f"{simulation.now:0.2f}:\tvVolume {volume.label} is allocated on vHost {self.label}."
        )
        simulation.volume_allocator.allocate()

    def cache_packet(self, packet: vPacket):
        """Cache a packet on the vHost."""
        self.ram.distribute(packet, packet.size)
        self.packets.append(packet)
        if not packet.scheduled:
            packet.status.append(SCHEDULED)
            packet._scheduled_at = simulation.now
        packet.status.append(QUEUED)
        packet._current_hop = self
        packet_handler = vPacketHandler(
            length=int(self.delay * self.cpu.single_core_capacity),
            packet=packet,
            host=self,
            at=simulation.now,
        )
        self.processes.append(packet_handler)
        self.cpu.cache_process(packet_handler)
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} cached packet {packet.label}."
        )

    @property
    def taint(self) -> str:
        """The taint of the vHost. Used during container scheduling."""
        return self._taint

    @property
    def containers(self) -> List[Entity]:
        """The containers on the vHost."""
        return self._containers

    @property
    def volumes(self) -> List[Entity]:
        """The volumes on the vHost."""
        return self._volumes

    @property
    def privisioned(self) -> bool:
        """return True if the vHost is privisioned, False otherwise."""
        return self._privisioned

    @property
    def delay(self) -> float:
        """the packet processing delay of the vHost."""
        return self._delay

    @property
    def cpu_reservor(self) -> Resource:
        """the reservor of the CPU of the vHost."""
        return self._cpu_reservor

    @property
    def ram_reservor(self) -> Resource:
        """the reservor of the RAM of the vHost."""
        return self._ram_reservor
