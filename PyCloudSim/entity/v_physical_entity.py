from __future__ import annotations
from math import inf, log
from typing import List, Union, Optional, Callable, TYPE_CHECKING
from abc import ABC

from Akatosh import Actor, Resource
from bitmath import GiB

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_physical_component import PhysicalComponent
from .v_cpu import vCPU

if TYPE_CHECKING:
    from .v_nic import vNIC
    from .v_packet import vPacket
    from .v_process import vProcess


class PhysicalEntity(PhysicalComponent, ABC):
    _privisoned_at: float

    def __init__(
        self,
        num_cpu_cores: int = 1,
        ipc: Union[int, float] = 1,
        frequency: Union[int, float] = 1000,
        ram: int = 1,
        rom: int = 1,
        delay: float = 0.01,
        idle_power=50,
        cpu_tdp=125,
        ram_tdp=50,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        super().__init__(at=at, after=after, label=label)
        self._cpu = vCPU(
            ipc=ipc, frequency=frequency, num_cores=num_cpu_cores, tdp=cpu_tdp
        )
        self._ram = Resource(
            capacity=GiB(ram).bytes, label=f"{self.__class__.__name__} {self.label} RAM"
        )
        self._rom = Resource(
            capacity=GiB(rom).bytes, label=f"{self.__class__.__name__} {self.label} ROM"
        )
        self._delay = delay
        self._privisoned_at = float()
        self._packets = list()
        self._interfaces: List[vNIC] = list()
        self._processes = list()
        self._packet_scheduler: Actor = None  # type: ignore
        self._idle_power = idle_power
        self._ram_tdp = ram_tdp
        simulation.topology.add_node(self)

    def send_packets(self):
        def _send_packets():
            if len(self.packets) > 0:
                LOGGER.debug(
                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is scheduling packets, queued packets: {len(self.packets)}."
                )
                self.packets.sort(key=lambda packet: packet.priority)
                for packet in self.packets:
                    if (
                        packet.decoded
                        and not packet.terminated
                        and not packet.transmitting
                    ):
                        LOGGER.debug(
                            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is sending packet {packet.label}."
                        )
                        for s_interface in self.interfaces:
                            if s_interface.connected_to is packet.next_hop:
                                LOGGER.debug(
                                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} found interface {s_interface.label} for packet {packet.label}."
                                )
                                for d_interface in packet.next_hop.interfaces:
                                    if d_interface.connected_to is self:
                                        LOGGER.debug(
                                            f"{simulation.now:0.2f}:\t{packet.next_hop.__class__.__name__} {packet.next_hop.label} found interface {d_interface.label} for packet {packet.label}."
                                        )
                                        delay = packet.size / min(
                                            [
                                                s_interface.bandwidth,
                                                d_interface.bandwidth,
                                            ]
                                        )
                                        if (
                                            s_interface.downlink.available_quantity
                                            >= packet.size
                                            and d_interface.uplink.available_quantity
                                            >= packet.size
                                        ):
                                            s_interface.send_packet(packet, delay)
                                            d_interface.receive_packet(packet, delay)
                                            LOGGER.info(
                                                f"{simulation.now:0.2f}:\tvPacket {packet.label} is in transmission from {self.__class__.__name__} {self.label} to {packet.next_hop.__class__.__name__} {packet.next_hop.label}"
                                            )
                                            break
                                break
            LOGGER.debug(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} scheduled all packets within the queue."
            )
            self._packet_scheduler = None  # type: ignore

        if self.packet_scheduler is None:
            self._packet_scheduler = Actor(
                at=simulation.now,
                action=_send_packets,
                label=f"{self.__class__.__name__} {self.label} Send Packets",
                priority=HOST_SCHEDULE_PACKET,
            )

    def uplink_utilization(self, inertval: float = 0.1) -> float:
        return float(
            sum(
                [
                    interface.uplink_utilization(inertval)
                    for interface in self.interfaces
                ]
            )
            / len(self.interfaces)
        )

    def downlink_utilization(self, inertval: float = 0.1) -> float:
        return float(
            sum(
                [
                    interface.downlink_utilization(inertval)
                    for interface in self.interfaces
                ]
            )
            / len(self.interfaces)
        )

    def power_usage(
        self, interval: Union[int, float] = 0.1, func: str = "log"
    ) -> float:
        cpu_usage = self.cpu.utilization_in_past(interval) * 100
        ram_usage = self.ram.utilization_in_past(interval) * 100
        if func == "log":
            cpu_power_usage = log((cpu_usage + 1), 100) * self.cpu_tdp
            ram_power_usage = log((ram_usage + 1), 100) * self.ram_tdp
            return cpu_power_usage + ram_power_usage + self.idle_power
        elif func == "linear":
            return (
                (cpu_usage * self.cpu_tdp / 100)
                + (ram_usage * self.ram_tdp / 100)
                + self.idle_power
            )
        else:
            raise ValueError(f"Unknown power usage function: {func}")

    @property
    def privisoned_at(self) -> float:
        return self._privisoned_at

    @property
    def privisoned(self) -> bool:
        return PRIVISIONED in self._status

    @property
    def powered_on(self) -> bool:
        return POWERED_ON in self._status

    @property
    def powered_off(self) -> bool:
        return POWERED_ON not in self._status

    @property
    def packets(self) -> List[vPacket]:
        return self._packets

    @property
    def interfaces(self) -> List[vNIC]:
        return self._interfaces

    @property
    def processes(self) -> List[vProcess]:
        return self._processes

    @property
    def cpu(self) -> vCPU:
        return self._cpu

    @property
    def ram(self) -> Resource:
        return self._ram

    @property
    def rom(self) -> Resource:
        return self._rom

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def packet_scheduler(self) -> Actor:
        return self._packet_scheduler

    @property
    def idle_power(self) -> float:
        return self._idle_power

    @property
    def cpu_tdp(self) -> float:
        return self.cpu.tdp

    @property
    def ram_tdp(self) -> float:
        return self._ram_tdp
