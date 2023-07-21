from __future__ import annotations
from random import choice
from typing import List, Optional, Union, Callable, TYPE_CHECKING
from ipaddress import IPv4Network, IPv4Address

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_physical_entity import PhysicalEntity
from .v_cpu import vCPU
from .v_nic import vNIC
from .v_process import vPacketHandler

from Akatosh import Actor, Resource
from bitmath import GiB

if TYPE_CHECKING:
    from .v_packet import vPacket
    from .v_host import vHost
    from .v_router import vRouter


class vSwitch(PhysicalEntity):
    def __init__(
        self,
        ipc: Union[int, float],
        frequency: Union[int, float],
        num_cpu_cores: int,
        ram: int,
        subnet: str,
        delay: float = 0.01,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a virtual switch.

        Args:
            ipc (Union[int, float]): the instructions per cycle of the CPU.
            frequency (Union[int, float]): the frequency of the CPU.
            num_cpu_cores (int): the number of CPU cores.
            ram (int): the amount of RAM in MiB.
            subnet (str): the subnet of the switch.
            delay (float, optional): the packet proccessing dekay. Defaults to 0.01.
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
        self._subnet = IPv4Network(subnet)
        self._usable_host_address = list(self.subnet.hosts())
        simulation.SWITCHES.append(self)

    def creation(self):
        """Creation process of the vSwitch.
        """
        return super().creation()

    def termination(self):
        """Termination process of the vSwitch.
        """
        return super().termination()

    def _power_on(self):
        """Power on process of the vSwitch."""
        super()._power_on()
        self.cpu.power_on()
        for interface in self.interfaces:
            interface.power_on()

    def _power_off(self):
        """Power off process of the vSwitch."""
        super()._power_off()
        self.cpu.power_off()
        for interface in self.interfaces:
            interface.power_off()

    def connect_device(self, device: Union[vHost, vRouter], bandwidth: int = 1000):
        """Connect a device to the vSwitch. A new vNIC will be created as a "Port" of the switch.

        Args:
            device (Union[vHost, vRouter]): the device to connect to the switch.
            bandwidth (int, optional): the bandwidth of this link. Defaults to 1000.
        """
        def _connect_device():
            port = vNIC(host=self, connected_to=device, bandwidth=bandwidth)
            self.interfaces.append(port)
            if device.__class__.__name__ == "vHost":
                interface = vNIC(host=device, connected_to=self, bandwidth=bandwidth)
                chosen_ip = choice(self.usable_host_address[1:-1])
                interface._ip = chosen_ip
                device.interfaces.append(interface)
                device.interfaces.append(interface)
                simulation.topology.add_weighted_edges_from(
                    [(self, device, min([bandwidth, interface.bandwidth]))]
                )
                simulation.topology.add_weighted_edges_from(
                    [(device, self, min([bandwidth, interface.bandwidth]))]
                )
            elif device.__class__.__name__ == "vRouter":
                interface = vNIC(host=device, connected_to=self, bandwidth=bandwidth)
                interface._ip = self.usable_host_address[0]
                device.interfaces.append(interface)
                simulation.topology.add_weighted_edges_from(
                    [(self, device, min([bandwidth, interface.bandwidth]))]
                )
                simulation.topology.add_weighted_edges_from(
                    [(device, self, min([bandwidth, interface.bandwidth]))]
                )
            else:
                raise TypeError(
                    f"Device {device.label} type {device.__class__.__name__} is not vHost or vRouter."
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
        """Cache a packet and engage the packet processing. This function is automatically called by the vNIC upon receiving any packet.

        Args:
            packet (vPacket): _description_
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
            at=simulation.now
        )
        self.processes.append(packet_handler)
        self.ram.distribute(packet_handler, packet_handler.length)
        self.cpu.cache_process(packet_handler)
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} cached packet {packet.label}."
        )

    @property
    def cpu(self) -> vCPU:
        """returns the CPU of the vSwitch."""
        return self._cpu

    @property
    def ram(self) -> Resource:
        """returns the RAM of the vSwitch."""
        return self._ram

    @property
    def subnet(self) -> IPv4Network:
        """returns the subnet of the vSwitch."""
        return self._subnet

    @property
    def usable_host_address(self) -> List[IPv4Address]:
        """returns the usable host addresses of the vSwitch."""
        return self._usable_host_address

    @property
    def delay(self) -> float:
        """returns the packet processing delay of the vSwitch."""
        return self._delay
