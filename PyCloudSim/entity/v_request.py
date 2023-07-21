from __future__ import annotations
from operator import index
from typing import List, TYPE_CHECKING, Union, Callable, Optional

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from ..requests import *
from .v_process import vProcess
from .v_packet import vPacket
from .v_microservice import vMicroservice
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity

if TYPE_CHECKING:
    from .v_sfc import vSFC
    from .v_user import vUser, WorkFlow
    from .v_container import vContainer


class vRequest(VirtualEntity):
    def __init__(
        self,
        source: Union[vUser, vMicroservice],
        target: Union[vUser, vMicroservice],
        flow: Optional[WorkFlow] = None,
        type: str = GET,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a request.

        Args:
            source (Union[vUser, vMicroservice]): the source of this request, can be vUser or vMicroservice.
            target (Union[vUser, vMicroservice]): the target of this request, can be vUser or vMicroservice.
            flow (Optional[WorkFlow], optional): the workflow of this request. Defaults to None.
            type (str, optional): type of the request, GET, POST, LIST, DELETE. Defaults to GET.
            at (Union[int, float, Callable], optional): when the request should be created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the entity that this request must be created after. Defaults to None.
            label (Optional[str], optional): short description of the request. Defaults to None.
        """
        super().__init__(at, after, label)
        self._source = source
        self._target = target
        self._flow = flow if flow else None
        if self.flow:
            if callable(self.flow.priority):
                self._priority = self.flow.priority()
            else:
                self._priority = self.flow.priority
        else:
            self._priority = 0
        self._processes = list()
        self._packets = list()
        self._source_endpoint: vContainer = None  # type: ignore
        self._target_endpoint: vContainer = None  # type: ignore
        self._type = type
        self._on_creation = simulation.request_scheduler.schedule
        
    def creation(self):
        if self.flow:
            if self.flow.failed:
                LOGGER.debug(f"{simulation.now:0.2f}:\tvRequest {self.label} creation cancelled due to Workflow {self.flow.label} failed.")
                return
        simulation.REQUESTS.append(self)
        return super().creation()
        

    def execute(self):
        """Exceute the request by initiating the processes and packets according to the request type.

        Raises:
            RuntimeError: raise if the request is not scheduled.
        """
        if self.scheduled:
            LOGGER.info(f"{simulation.now:0.2f}:\tvRequest {self.label} is executing.")
            if self.flow is not None:
                if callable(self.flow.process_length):
                    process_length = self.flow.process_length()
                else:
                    process_length = self.flow.process_length
            else:
                process_length = 100

            if self.flow is not None:
                if callable(self.flow.packet_size):
                    packet_size = self.flow.packet_size()
                else:
                    packet_size = self.flow.packet_size
            else:
                packet_size = 65536

            if self.flow is not None:
                if callable(self.flow.num_packets):
                    num_packets = self.flow.num_packets()
                else:
                    num_packets = self.flow.num_packets
            else:
                num_packets = 1

            if self.type == GET:
                self.execute_get(process_length, packet_size, num_packets)
            elif self.type == POST:
                self.execute_post(process_length, packet_size, num_packets)
            elif self.type == LIST:
                self.execute_list(process_length, packet_size, num_packets)

        else:
            raise RuntimeError(f"vRequest {self.label} is not scheduled.")

    def execute_get(self, process_length: int, packet_size: int, num_packets: int):
        """Execute the get type request.

        Args:
            process_length (int): the length of the process, given by the workflow.
            packet_size (int): the size of the packet, given by the workflow.
            num_packets (int): the number of packets, given by the workflow.
        """
        physical_source = (
            self.source_endpoint.host
            if self.source_endpoint is not None
            else simulation.gateway
        )
        physical_destination = (
            self.target_endpoint.host
            if self.target_endpoint is not None
            else simulation.gateway
        )

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-get",
            )
        else:
            process = None

        packets = list()
        packet = vPacket(
            source=physical_source,
            destination=physical_destination,
            request=self,
            size=packet_size,
            at=simulation.now,
            after=process,
            label=f"{self.label}-get",
        )
        self.packets.append(packet)
        packets.append(packet)

        if self.target.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.target_endpoint,
                at=simulation.now,
                label=f"{self.label}-reply",
                after=packets,
            )
        else:
            process = None

        packets.clear()
        for _ in range(num_packets):
            packet = vPacket(
                source=physical_destination,
                destination=physical_source,
                request=self,
                size=packet_size,
                at=simulation.now,
                after=process,
                label=f"{self.label}-reply",
            )
            self.packets.append(packet)
            packets.append(packet)

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-ack",
                after=packets,
            )
        else:
            process = None

        packet = vPacket(
            source=physical_destination,
            destination=physical_source,
            request=self,
            size=packet_size,
            at=simulation.now,
            after=process if process is not None else packets,
            label=f"{self.label}-ack",
        )
        packet._on_termination = (
            lambda: self.complete() if packet.completed and not self.failed else None
        )
        self.packets.append(packet)
        packets.append(packet)

    def execute_post(self, process_length: int, packet_size: int, num_packets: int):
        """Execute the post type request.

        Args:
            process_length (int): the length of the process, given by the workflow.
            packet_size (int): the size of the packet, given by the workflow.
            num_packets (int): the number of packets, given by the workflow.
        """
        physical_source = (
            self.source_endpoint.host
            if self.source_endpoint is not None
            else simulation.gateway
        )
        physical_destination = (
            self.target_endpoint.host
            if self.target_endpoint is not None
            else simulation.gateway
        )

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-post",
            )
        else:
            process = None

        packets = list()
        for _ in range(num_packets):
            packet = vPacket(
                source=physical_source,
                destination=physical_destination,
                request=self,
                size=packet_size,
                at=simulation.now,
                after=process,
                label=f"{self.label}-post",
            )
            self.packets.append(packet)
            packets.append(packet)

        if self.target.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.target_endpoint,
                at=simulation.now,
                label=f"{self.label}-ack",
                after=packets,
            )
        else:
            process = None

        packets.clear()
        for _ in range(num_packets):
            packet = vPacket(
                source=physical_destination,
                destination=physical_source,
                request=self,
                size=packet_size,
                at=simulation.now,
                after=process,
                label=f"{self.label}-ack",
            )
            self.packets.append(packet)
            packets.append(packet)

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-ack",
                after=packets,
            )
            process._on_termination = (
                lambda: self.complete()
                if process and process.completed and not self.failed
                else None
            )
        else:
            process = None
            packets[-1].on_termination = (
                lambda: self.complete()
                if packets[-1].completed and not self.failed
                else None
            )

    def execute_list(self, process_length: int, packet_size: int, num_packets: int):
        """Execute the list type request.

        Args:
            process_length (int): the length of the process, given by the workflow.
            packet_size (int): the size of the packet, given by the workflow.
            num_packets (int): the number of packets, given by the workflow.
        """
        physical_source = (
            self.source_endpoint.host
            if self.source_endpoint is not None
            else simulation.gateway
        )
        physical_destination = (
            self.target_endpoint.host
            if self.target_endpoint is not None
            else simulation.gateway
        )

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-get",
            )
        else:
            process = None

        packets = list()
        packet = vPacket(
            source=physical_source,
            destination=physical_destination,
            request=self,
            size=packet_size,
            at=simulation.now,
            after=process,
            label=f"{self.label}-get",
        )
        self.packets.append(packet)
        packets.append(packet)

        if self.target.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.target_endpoint,
                at=simulation.now,
                label=f"{self.label}-reply",
                after=packets,
            )
        else:
            process = None

        packets.clear()
        for _ in range(num_packets):
            packet = vPacket(
                source=physical_destination,
                destination=physical_source,
                request=self,
                size=packet_size,
                at=simulation.now,
                after=process,
                label=f"{self.label}-reply",
            )
            self.packets.append(packet)
            packets.append(packet)

        if self.source.__class__.__name__ != "vUser":
            process = vProcess(
                process_length,
                priority=self.priority,
                request=self,
                container=self.source_endpoint,
                at=simulation.now,
                label=f"{self.label}-ack",
                after=packets,
            )
        else:
            process = None

        packet = vPacket(
            source=physical_destination,
            destination=physical_source,
            request=self,
            size=packet_size,
            at=simulation.now,
            after=process if process is not None else packets,
            label=f"{self.label}-ack",
        )
        packet._on_termination = (
            lambda: self.complete() if packet.completed and not self.failed else None
        )
        self.packets.append(packet)
        packets.append(packet)

    def termination(self):
        """Terminate the request by terminating all the processes, and remove the request from the source and target endpoints."""
        super().termination()

        if self.scheduled:
            if self.source_endpoint is not None:
                self.source_endpoint.requests.remove(self)
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvRequest {self.label} removed from {self.source_endpoint.label}."
                )
            if self.target_endpoint is not None:
                self.target_endpoint.requests.remove(self)
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvRequest {self.label} removed from {self.target_endpoint.label}."
                )
        simulation.request_scheduler.schedule()

    def complete(self):
        """Complete the request and engage the termination of the request."""
        if not self.completed:
            self.status.append(COMPLETED)
            self.terminate()
            LOGGER.info(f"{simulation.now:0.2f}:\tvRequest {self.label} completed.")

    def fail(self):
        """Fail the request and engage the termination of the request."""
        if not self.failed:
            self.status.append(FAILED)
            self.terminate()
            LOGGER.info(f"{simulation.now:0.2f}:\tvRequest {self.label} failed.")
            if self.flow is not None:
                self.flow.fail()

    @property
    def source(self) -> Union[vUser, vMicroservice]:
        return self._source

    @property
    def source_endpoint(self) -> vContainer:
        return self._source_endpoint

    @property
    def target(self) -> Union[vUser, vMicroservice]:
        return self._target

    @property
    def target_endpoint(self) -> vContainer:
        return self._target_endpoint

    @property
    def processes(self) -> List[vProcess]:
        return self._processes

    @property
    def user(self) -> Optional[vUser]:
        if self.flow:
            return self.flow.user
        else:
            return None

    @property
    def flow(self):
        return self._flow

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def ram_usage(self) -> int:
        return sum([process.ram_usage for process in self.processes])

    @property
    def packets(self) -> List[vPacket]:
        return self._packets

    @property
    def type(self) -> str:
        return self._type
