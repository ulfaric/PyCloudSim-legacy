from __future__ import annotations
from abc import ABC
from lib2to3.fixes.fix_renames import LOOKUP
from math import inf
from random import randbytes, randint
import re
from typing import TYPE_CHECKING, List, Optional, Union, Callable

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity

from PyCloudSim.core import X86_64, ARM

if TYPE_CHECKING:
    from .v_microservice import vContainer
    from .v_cpu_core import vCPUCore
    from .v_cpu import vCPU
    from .v_host import vHost
    from .v_packet import vPacket
    from .v_request import vRequest
    from .v_switch import vSwitch
    from .v_router import vRouter


class vInstruction(ABC):
    def __init__(self) -> None:
        """Create a vInstruction.
        """
        super().__init__()
        self._content = bytes()

    @property
    def content(self) -> bytes:
        """Return the content of the vInstruction."""
        return self._content

    @property
    def length(self) -> int:
        """Return the length of the vInstruction."""
        return len(self.content)


class vX86Instruction(vInstruction):
    def __init__(self) -> None:
        """Create a vX86Instruction."""
        super().__init__()
        self._content = randbytes(randint(1, 16))


class vARMInstruction(vInstruction):
    def __init__(self) -> None:
        """Create a vARMInstruction."""
        super().__init__()
        self._content = randbytes(4)


class vProcess(VirtualEntity):
    def __init__(
        self,
        length: int,
        priority: Union[int, float],
        request: Optional[vRequest] = None,
        container: Optional[vContainer] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vProcess.

        Args:
            length (int): the length in terms of instructions.
            priority (Union[int, float]): the priority of the vProcess.
            request (Optional[vRequest], optional): the request that the vProcess is associated with. Defaults to None.
            container (Optional[vContainer], optional): the container that the vProcess is on. Defaults to None.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(at, after, label)
        self._length = length
        self._priority = priority
        self._instructions = list()
        self._request_id = request.id if request else None
        self._container_id = container.id if container else None
        self._host_id = int()
        self._cpu_id = int()
        self._cpu_core_id = int()
        self._progress = 0
        self._current_scheduled_length = 0
        self._executing_cores: List[vCPUCore] = list()
        if self.request is not None:
            self.request.processes.append(self)
        self.on_creation = lambda: self.container.accept_process(self) if self.container else None

    def creation(self):
        """The creation process of a vProcess."""
        if self.request:
            if self.request.failed:
                LOGGER.debug(f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} creation cancelled due to vRequest {self.request.label} failed.")
                return
        
        # generate instructions and wrap them as priority items
        self._instructions = list()
        for _ in range(self.length):
            if simulation.platform == X86_64:
                instruction = vX86Instruction()
                self.instructions.append(instruction)
            if simulation.platform == ARM:
                instruction = vARMInstruction()
                self.instructions.append(instruction)
        simulation.PROCESSES.append(self)
        return super().creation()

    def termination(self):
        """The termination process of a vProcess."""
        super().terminate()
        self.release_resources()

        if self.cached:
            self.cpu.schedule_process()

    def release_resources(self):
        """Release the resources that the vProcess is holding."""
        if self.scheduled and self.container:
            self.container.processes.remove(self)
            self.container.ram.release(self)
            self.container.cpu.release(self)
            for claim in self.container.cpu.claims:
                if claim.user is self:
                    LOGGER.error(
                        f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} failed to release CPU resources from vContainer {self.container.label}, remaining {claim.quantity} CPU"
                    )
                    raise RuntimeError()
            LOGGER.debug(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} release resources from vContainer {self.container.label}"
            )
            LOGGER.debug(
                f"{simulation.now:0.2f}:\tvContainer {self.container.label}: {self.container.cpu.available_quantity} CPU, {self.container.ram.available_quantity} RAM, {len(self.container.processes)} Processes."
            )

        if self.cached:
            self.host.processes.remove(self)
            self.host.ram.release(self)
            self.cpu.processes.remove(self)
            if self.executing:
                for core in self.executing_cores:
                    core.processes.remove(self)
                    core.computational_power.release(self)
            LOGGER.debug(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} release resources from vHost {self.host.label}"
            )
            LOGGER.debug(
                f"{simulation.now:0.2f}:\tvHost {self.host.label}: {self.host.cpu.availablity} CPU, {self.host.ram.available_quantity} RAM"
            )

    def crash(self):
        """Crash the vProcess."""
        if not self.failed:
            self.status.append(FAILED)
            self.terminate()
            LOGGER.info(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} failed"
            )
            if self.request:
                if not self.request.failed:
                    self.request.fail()

    def complete(self):
        """Complete the vProcess."""
        if not self.completed and not self.failed and not self.terminated:
            if self.remaining <= 0:
                self.status.append(COMPLETED)
                self.terminate()
                LOGGER.info(
                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} completed"
                )

    @property
    def length(self) -> int:
        """Return the length of the vProcess."""
        return self._length

    @property
    def priority(self) -> Union[int, float]:
        """Return the priority of the vProcess."""
        return self._priority

    @property
    def instructions(self) -> List[vInstruction]:
        """Return the instructions of the vProcess."""
        return self._instructions

    @property
    def ram_usage(self) -> int:
        """Return the RAM usage of the vProcess."""
        return (
            sum([instruction.length for instruction in self.instructions])
            * simulation.ram_amplifier
        )

    @property
    def container_id(self) -> int | None:
        """Return the container id of the vProcess."""
        return self._container_id

    @property
    def host_id(self) -> int:
        """Return the host id of the vProcess."""
        return self._host_id

    @property
    def request_id(self) -> Optional[int]:
        """Return the request id of the vProcess."""
        return self._request_id

    @property
    def container(self) -> vContainer | None:
        """Return the container of the vProcess."""
        if self.container_id is None:
            return None
        else:
            for container in simulation.CONTAINERS:
                if container.id == self.container_id:
                    return container
            raise RuntimeError(
                f"{self.__class__.__name__} {self.label} is not associated with any vContainer."
            )

    @property
    def host(self) -> vHost:
        """Return the host of the vProcess."""
        for host in simulation.HOSTS:
            if host.id == self.host_id:
                return host
        raise RuntimeError(
            f"{self.__class__.__name__} {self.label} is not found on any vHost."
        )

    @property
    def request(self) -> Optional[vRequest]:
        """Return the request of the vProcess."""
        if self.request_id is None:
            return None
        else:
            for request in simulation.REQUESTS:
                if request.id == self.request_id:
                    return request
            raise RuntimeError(
                f"{self.__class__.__name__} {self.label} is not associated with any vRequest."
            )

    @property
    def cpu_id(self) -> int:
        """Return the cpu id of the vProcess."""
        return self._cpu_id

    @property
    def cpu(self) -> vCPU:
        """Return the cpu of the vProcess."""
        for cpu in simulation.CPUS:
            if cpu.id == self.cpu_id:
                return cpu
        raise RuntimeError(
            f"{self.__class__.__name__} {self.label} is not associated with any vCPU."
        )

    @property
    def cpu_core_id(self) -> int:
        """Return the cpu core id of the vProcess."""
        return self._cpu_core_id

    @property
    def cpu_core(self) -> vCPUCore:
        """Return the cpu core of the vProcess."""
        for cpu_core in simulation.CPU_CORES:
            if cpu_core.id == self.cpu_core_id:
                return cpu_core
        raise RuntimeError(
            f"{self.__class__.__name__} {self.label} is not associated with any vCPU Core."
        )

    @property
    def cached(self) -> bool:
        """Return whether the vProcess is cached or not."""
        return CACHED in self.status

    @property
    def executing(self) -> bool:
        """Return whether the vProcess is executing or not."""
        return EXECUTING in self.status

    @property
    def progress(self) -> int:
        """Return the progress of the vProcess."""
        return self._progress

    @property
    def remaining(self) -> int:
        """Return the remaining length of the vProcess."""
        return self.length - self.progress

    @property
    def current_scheduled_length(self) -> int:
        """Return the current scheduled length of the vProcess."""
        return self._current_scheduled_length

    @property
    def executing_cores(self) -> List[vCPUCore]:
        """Return the executing cores of the vProcess."""
        return self._executing_cores


class vDeamonProcess(vProcess):
    def __init__(
        self,
        length: int,
        container: vContainer,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vDeamonProcess.

        Args:
            length (int): the length in terms of instructions.
            container (vContainer): the cache that the vDeamonProcess is on.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(length=length, priority=-inf, at=at, after=after, label=label)
        self._container_id = container.id

    def creation(self):
        """Creation process of a vDeamonProcess."""
        super().creation()
        self.container.accept_process(self)

    def termination(self):
        """Termination process of a vDeamonProcess."""
        super(vProcess, self).termination()
        if not self.failed:
            self.release_resources()
            self.container.init_deamon()
        else:
            self.release_resources()

    @property
    def container_id(self) -> int:
        """The container id of the vDeamonProcess."""
        return self._container_id

    @property
    def container(self) -> vContainer:
        """The container of the vDeamonProcess."""
        for container in simulation.CONTAINERS:
            if container.id == self.container_id:
                return container
        raise RuntimeError(
            f"{self.__class__.__name__} {self.label} is not associated with any vContainer."
        )


class vPacketHandler(vProcess):
    def __init__(
        self,
        length: int,
        packet: vPacket,
        host: Union[vHost, vSwitch, vRouter],
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vPacketHandler.

        Args:
            length (int): the length of the vPacketHandler, will be determined by processing delay.
            packet (vPacket): the assoicated vPacket.
            host (Union[vHost, vSwitch, vRouter]): the host that the vPacketHandler is on.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(
            length=length,
            priority=packet.request.priority if packet.request else 0,
            at=at,
            after=after,
            label=label,
        )
        self._packet_id = packet.id
        self._host = host

    def creation(self):
        """The creation process of a vPacketHandler."""
        super().creation()

    def termination(self):
        """The termination process of a vPacketHandler."""
        super(vProcess, self).termination()
        self.release_resources()
        self.packet.status.append(DECODED)
        LOGGER.debug(f"{simulation.now:0.2f}:\tvPacket {self.packet.label} is decoded.")
        self.packet.current_hop.send_packets()

    def complete(self):
        """Complete the vPacketHandler."""
        if not self.completed and not self.failed and not self.terminated:
            if self.remaining <= 0:
                self.status.append(COMPLETED)
                self.terminate()
                LOGGER.info(
                    f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} completed"
                )
                if self.packet.path[-1] is self.packet.current_hop:
                    self.packet.complete()

    @property
    def packet_id(self) -> int:
        """The id of the associated vPacket."""
        return self._packet_id

    @property
    def packet(self) -> vPacket:
        """The associated vPacket."""
        for packet in simulation.PACKETS:
            if packet.id == self.packet_id:
                return packet
        raise RuntimeError(
            f"vPacketHandler {self.label} is not associated with any vPacket."
        )

    @property
    def host(self) -> Union[vHost, vSwitch, vRouter]:
        """The host that the vPacketHandler is on."""
        return self._host
