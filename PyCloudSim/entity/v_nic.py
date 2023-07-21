from __future__ import annotations
from ipaddress import IPv4Address
from operator import index
from typing import List, Union, TYPE_CHECKING, Callable, Optional

from matplotlib.style import available

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_physical_component import Entity, PhysicalComponent
from .v_process import vPacketHandler

from Akatosh import Actor, Resource
from bitmath import MiB

if TYPE_CHECKING:
    from .v_host import vHost
    from .v_packet import vPacket
    from .v_router import vRouter
    from .v_gateway import vGateway
    from .v_switch import vSwitch


class vNIC(PhysicalComponent):
    def __init__(
        self,
        host: Union[vHost, vRouter, vSwitch, vGateway],
        connected_to: Optional[Union[vHost, vRouter, vSwitch, vGateway]] = None,
        bandwidth: int = 1000,
        delay: float = 0.02,
        ip: Optional[IPv4Address] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vNIC object.

        Args:
            host (Union[vHost, vRouter, vSwitch, vGateway]): the host that the vNIC is attached to.
            connected_to (Optional[Union[vHost, vRouter, vSwitch, vGateway]], optional): the device that the vNIC is connected to. Defaults to None.
            bandwidth (int, optional): the bandwidth in MBps of the vNIC. Defaults to 1000.
            delay (float, optional): the processing delay of the vNIC. Defaults to 0.02.
            ip (Optional[IPv4Address], optional): the IP address of the vNIC. Defaults to None.
            at (Union[int, float, Callable], optional): same as Entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as Entity. Defaults to None.
            label (Optional[str], optional): Same as Entity. Defaults to None.
        """
        super().__init__(at, after, label)
        self._host = host
        self._connected_to = connected_to
        self._bandwidth = MiB(bandwidth)
        self._delay = delay
        self._ip = ip
        if host.__class__.__name__ == "vHost" or host.__class__.__name__ == "vRouter":
            self._type = "Interface"
        else:
            self._type = "Port"
        self._uplink = Resource(
            capacity=self.bandwidth, label=f"vNIC {self.label} Uplink"
        )
        self._downlink = Resource(
            capacity=self.bandwidth, label=f"vNIC {self.label} Downlink"
        )
        simulation.NICS.append(self)

    def creation(self):
        """Creation process of the vNIC"""
        return super().creation()

    def termination(self):
        """Termination process of the vNIC"""
        return super().termination()

    def _power_on(self):
        """Power on the vNIC"""
        return super()._power_on()

    def _power_off(self):
        """Power off the vNIC"""
        return super()._power_off()

    def receive_packet(self, packet: vPacket, delay: float = 0.0):
        """Rceive a vPacket, the vPacket will be dropped if the attached host does not have enough RAM.

        Args:
            packet (vPacket): the vPacket to be recevived.
            delay (float, optional): the delay for receiving this vPacket in term of transmitting time. Defaults to 0.0.
        """
        self.uplink.distribute(packet, packet.size)
        LOGGER.debug(
            f"{simulation.now:0.2f}:\tvPacket {packet.label} is using {packet.size}/{self.uplink.available_quantity}/{self.uplink.capacity} bytes of vNIC {self.label} uplink."
        )

        def _received_packet():
            self.uplink.release(packet)
            packet.status.remove(TRANSMITTING)
            packet.status.remove(DECODED)
            try:
                self.host.cache_packet(packet)
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvPacket {packet.label} is received by {self.host.__class__.__name__} {self.host.label}"
                )
            except:
                packet.drop()
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvPacket {packet.label} is droped by {self.host.__class__.__name__} {self.host.label}"
                )

        Actor(
            at=simulation.now + delay,
            action=_received_packet,
            label=f"vNIC {self.label} Receive Packet",
            priority=CORE_EXECUTE_PROCESS,
        )

    def send_packet(self, packet: vPacket, delay: float = 0.0):
        """Send a vPacket.

        Args:
            packet (vPacket): the vPacket to be sent.
            delay (float, optional): the delay for sending this packet in term of transmitting time. Defaults to 0.0.
        """
        self.downlink.distribute(packet, packet.size)
        LOGGER.debug(
            f"{simulation.now:0.2f}:\tvPacket {packet.label} is using {packet.size}/{self.downlink.available_quantity}/{self.downlink.capacity} bytes of vNIC {self.label} downlink."
        )
        self.host.packets.remove(packet)
        packet.status.append(TRANSMITTING)
        packet.status.remove(QUEUED)

        def _sent_packet():
            self.downlink.release(packet)
            if self.host.__class__.__name__ == "vGateway":
                pass
            else:
                self.host.ram.release(packet)  # type: ignore
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvPacket {packet.label} is sent by {self.host.__class__.__name__} {self.host.label}"
            )
            Actor(
                at=simulation.now,
                action=self.host.send_packets,
                label=f"{self.__class__.__name__} {self.label} Send Packets",
                priority=HOST_SCHEDULE_PACKET,
            )

        Actor(
            at=simulation.now + delay,
            action=_sent_packet,
            label=f"vNIC {self.label} Send Packet",
            priority=CORE_EXECUTE_PROCESS,
        )

    @property
    def host(self) -> Union[vHost, vRouter, vSwitch, vGateway]:
        """The attached host."""
        return self._host

    @property
    def connected_to(self) -> Optional[Union[vHost, vRouter, vSwitch, vGateway]]:
        """The connected device."""
        return self._connected_to

    @property
    def bandwidth(self) -> float:
        """The bandwidth of the vNIC in MB/s."""
        return self._bandwidth.bytes

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def ip(self) -> Optional[IPv4Address]:
        """The IP address of the vNIC."""
        if self.type == "Interface":
            return self._ip
        else:
            return None

    @property
    def type(self) -> str:
        """The type of the vNIC."""
        return self._type

    @property
    def uplink(self) -> Resource:
        """The uplink of the vNIC."""
        return self._uplink

    @property
    def downlink(self) -> Resource:
        """The downlink of the vNIC."""
        return self._downlink

    def downlink_utilization(self, inertval: float = 0.1) -> float:
        """The downlink utilization of the vNIC in percentage."""
        return self.downlink.utilization_in_past(inertval) * 100

    def uplink_utilization(self, inertval: float = 0.1) -> float:
        """The uplink utilization of the vNIC in percentage."""
        return self.uplink.utilization_in_past(inertval) * 100
