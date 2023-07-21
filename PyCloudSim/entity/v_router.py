from __future__ import annotations

from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Callable, List, Optional, Union

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..priority import *
from ..status import *
from .v_entity import Entity
from .v_nic import vNIC
from .v_physical_entity import PhysicalEntity
from .v_process import vPacketHandler

if TYPE_CHECKING:
    from .v_gateway import vGateway
    from .v_packet import vPacket
    from .v_switch import vSwitch


class vRouter(PhysicalEntity):
    def __init__(
        self,
        ipc: Union[int, float],
        frequency: Union[int, float],
        num_cpu_cores: int,
        ram: int,
        delay: float = 0.01,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a virtual router.

        Args:
            ipc (Union[int, float]): the instructions per cycle of the CPU.
            frequency (Union[int, float]): the frequency of the CPU.
            num_cpu_cores (int): the number of CPU cores.
            ram (int): the amount of RAM in MiB.
            delay (float, optional): the packet processing delay. Defaults to 0.01.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(
            num_cpu_cores=num_cpu_cores,
            ipc=ipc,
            frequency=frequency,
            ram=ram,
            rom=1,
            delay=delay,
            at=at,
            after=after,
            label=label,
        )

    def creation(self):
        """The creation process of the vRouter"""
        return super().creation()

    def termination(self):
        """The termination process of the vRouter"""
        return super().termination()

    def _power_on(self):
        """Power on the vRouter"""
        super()._power_on()
        self.cpu.power_on()
        for interface in self.interfaces:
            interface.power_on()

    def _power_off(self):
        """Power off the vRouter"""
        super()._power_off()
        self.cpu.power_off()
        for interface in self.interfaces:
            interface.power_off()

    def connect_device(self, device: Union[vSwitch, vGateway], bandwidth: int = 1000):
        """Connect the vRouter to a device.

        Args:
            device (Union[vSwitch, vGateway]): the device to connect to.
            bandwidth (int, optional): the bandwidth of this link. Defaults to 1000.
        """
        def _connect_device():
            if (
                device.__class__.__name__ != "vSwitch"
                and device.__class__.__name__ != "vGateway"
            ):
                raise TypeError(
                    f"Device {device.label} type {device.__class__.__name__} is not vSwitch."
                )
            elif device.__class__.__name__ == "vSwitch":
                interface = vNIC(host=self, connected_to=device, bandwidth=bandwidth)
                interface._ip = device.usable_host_address[0]  # type: ignore
                self.interfaces.append(interface)
                port = vNIC(host=device, connected_to=self, bandwidth=bandwidth)
                device.interfaces.append(port)
                simulation.topology.add_weighted_edges_from(
                    [(self, device, min([bandwidth, interface.bandwidth]))]
                )
                simulation.topology.add_weighted_edges_from(
                    [(device, self, min([bandwidth, interface.bandwidth]))]
                )
                LOGGER.info(
                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} connected to {device.__class__.__name__} {device.label}."
                )
            elif device.__class__.__name__ == "vGateway":
                interface = vNIC(host=self, connected_to=device, bandwidth=bandwidth)
                interface._ip = IPv4Address("0.0.0.0")
                self.interfaces.append(interface)
                port = vNIC(host=device, connected_to=self, bandwidth=bandwidth)
                device.interfaces.append(port)
                simulation.topology.add_weighted_edges_from(
                    [(self, device, min([bandwidth, interface.bandwidth]))]
                )
                simulation.topology.add_weighted_edges_from(
                    [(device, self, min([bandwidth, interface.bandwidth]))]
                )
                LOGGER.info(
                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} connected to {device.__class__.__name__} {device.label}."
                )

        Actor(
            at=simulation.now,
            action=_connect_device,
            label=f"Connect {self.__class__.__name__} {self.label} to {device.__class__.__name__} {device.label}",
            priority=CREATION,
        )

    def cache_packet(self, packet: vPacket):
        """Cache a packet, this function will be automatically called by the vNIC upon receiving a packet.

        Args:
            packet (vPacket): the received packet.
        """
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
        self.ram.distribute(packet_handler, packet_handler.length)
        self.cpu.cache_process(packet_handler)
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} cached packet {packet.label}."
        )
