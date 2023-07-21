from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Union

from Akatosh import Resource
from bitmath import MiB

from ..core import simulation
from ..logger import LOGGER
from ..priority import *
from ..status import *
from .v_entity import Entity
from .v_process import vDeamonProcess, vProcess
from .v_virtual_entity import VirtualEntity
from .v_volume import vVolume

if TYPE_CHECKING:
    from .v_host import vHost
    from .v_microservice import vMicroservice
    from .v_request import vRequest


class vContainer(VirtualEntity):
    def __init__(
        self,
        cpu: int,
        cpu_limit: int,
        ram: int,
        ram_limit: int,
        image_size: int,
        volumes: Optional[List[Tuple[str, str, int, bool]]] = None,
        deamon: bool = False,
        taint: Optional[str] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a container with given specifications. Equivalent to a virtual machine or Pod in Kubernetes.

        Args:
            cpu (int): the amount of CPU requested by the container.
            cpu_limit (int): the maximum amount of CPU that the container can use.
            ram (int): the amount of RAM requested by the container.
            ram_limit (int): the maximum amount of RAM that the container can use.
            image_size (int): the size of the image that the container is running, in MB.
            volumes (Optional[List[Tuple[str, str, int, bool]]], optional): the volumes that attaches to this container, (name, path, size in MB, persistent or not). Defaults to None.
            deamon (bool, optional): set true will enable a deamon process for the container. Defaults to False.
            taint (Optional[str], optional): the container taint, using for host allocation. Defaults to None.
            at (Union[int, float, Callable], optional): when the container is created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the container must be created after the given entity is terminated. Defaults to None.
            label (Optional[str], optional): short description of the container. Defaults to None.
        """
        super().__init__(at=at, after=after, label=label)

        self._cpu_request = cpu
        self._cpu = Resource(
            capacity=cpu_limit, label=f"{self.__class__.__name__} {self.label} CPU"
        )
        self._ram_request = ram
        self._ram = Resource(
            capacity=MiB(ram_limit).bytes,
            label=f"{self.__class__.__name__} {self.label} RAM",
        )

        self._image_size = MiB(image_size)
        self._volumes = list()
        if volumes is None:
            self._volumes: List[vVolume] = list()
        else:
            for volume in volumes:
                new_volume = vVolume(volume[0], volume[1], volume[2], volume[3])
                new_volume.attach(self)
                self._volumes.append(new_volume)

        self._deamon = deamon
        self._taint = taint or str()
        self._host_id = int()
        self._microservice_id = int()
        self._processes: List[vProcess] = list()
        self._requests: List[vRequest] = list()
        self._on_creation = lambda: simulation.container_scheduler.schedule()
        simulation.CONTAINERS.append(self)

    def init_deamon(self):
        """Initialize the deamon process for the container."""
        if self.deamon:
            deamon = vDeamonProcess(
                length=int(
                    self.cpu_request / 1000 * self.host.cpu.single_core_capacity
                ),
                container=self,
                at=simulation.now,
                label=f"vContainer {self.label} Deamon",
            )

    def accept_request(self, request: vRequest):
        """Accept the vRequest"""
        self.requests.append(request)
        LOGGER.debug(
            f"{simulation.now:0.2f}:\tvContainer {self.label} accepts vRequest {request.label}."
        )

    def accept_process(self, process: vProcess):
        """Accept a process to run in the container."""
        if self.terminated:
            print(process.status)
            print(process.request.status)  # type: ignore
            print(self.label)
            raise Exception()

        self.processes.append(process)
        process._container_id = self.id
        process.status.append(SCHEDULED)
        # check if the container has enough ram resources to run the process
        try:
            self.ram.distribute(process, process.ram_usage)
        except:
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvContainer {self.label} is crushed by vProcess {process.label} due to RAM overload."
            )
            self.crash()
            return
        # check if the container's host has enough RAM
        try:
            self.host.ram.distribute(process, process.ram_usage)
        except:
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvContainer {self.label} is crushed by vProcess {process.label} due to vHost {self.host.label} RAM overload."
            )
            self.crash()
            return
        self.host.processes.append(process)
        self.host.cpu.cache_process(process)
        process._host_id = self.host.id
        LOGGER.info(
            f"{simulation.now:0.2f}:\tvProcess {process.label} is accepted by vContainer {process.container.label}."  # type: ignore
        )

    def termination(self):
        """Terminate the container. Any process running in the container will be terminated as well and marked as failed.

        Raises:
            RuntimeError: raise if there is a volume that should not be attached to the container.
        """
        # deallocate the container from the host if it is scheduled
        if self.scheduled:
            self.host.containers.remove(self)
            self.host.rom.release(self)
            self.host.cpu_reservor.release(self)
            self.host.ram_reservor.release(self)
        # detach or terminate all the volumes attached to the container
        detached_volumes: List[vVolume] = list()
        for volume in self.volumes:
            if volume.container is not self:
                raise RuntimeError(
                    f"Virtual Volume {volume.label} is should not be attached to vContainer {self.label}."
                )

            if volume.retain:
                volume.detach()
                detached_volumes.append(volume)
            else:
                volume.terminate()

        # terminate all the processes running in the container
        for process in self.processes:
            if not process.terminated:
                process.crash()

        for request in self.requests:
            if not request.terminated:
                request.fail()

        # recover the container if neccessary
        self.microservice.containers.remove(self)
        if self.failed:
            self.microservice.recover(self, detached_volumes)

        simulation.container_scheduler.schedule()

    def crash(self):
        """Crash the container. Any process running in the container will be terminated as well and marked as failed. This will call terminate() method."""

        if not self.failed:
            self.status.append(FAILED)
            self.terminate()
            LOGGER.info(f"{simulation.now:0.2f}:\tvContainer {self.label} Crashed.")

    @property
    def cpu_request(self) -> int:
        """return the CPU request of the container in millicore."""
        return self._cpu_request

    @property
    def cpu(self) -> Resource:
        """return the CPU ( as Resource ) of the container."""
        return self._cpu

    @property
    def ram_request(self) -> int:
        """return the RAM request of the container in MiB."""
        return self._ram_request

    @property
    def ram(self) -> Resource:
        """return the RAM ( as Resource ) of the container."""
        return self._ram

    @property
    def image_size(self) -> int:
        """return the image size of the container in bytes."""
        return self._image_size.bytes

    @property
    def rom_request(self) -> float:
        """return the ROM request of the container in MiB, which is the sum of the image size and the size of the volumes attached to the container."""
        return sum([volume.size for volume in self._volumes]) + self.image_size

    @property
    def volumes(self) -> List[vVolume]:
        """return the list of volumes attached to the container."""
        return self._volumes

    @property
    def taint(self) -> str:
        """return the taint of the container."""
        return self._taint

    @property
    def host_id(self) -> int:
        """return the id of the host that the container is scheduled to."""
        return self._host_id

    @property
    def host(self) -> vHost:
        """return the host that the container is scheduled to."""
        for host in simulation.HOSTS:
            if host.id == self.host_id:
                return host
        raise RuntimeError(f"Container {self.label} is not allocated to any host.")

    @property
    def microservice_id(self) -> int:
        """return the id of the microservice that the container is associated to."""
        return self._microservice_id

    @property
    def microservice(self) -> vMicroservice:
        """return the microservice that the container is associated to."""
        for microservice in simulation.MICROSERVICES:
            if microservice.id == self.microservice_id:
                return microservice
        raise RuntimeError(
            f"Container {self.label} is not allocated to any microservice."
        )

    @property
    def processes(self) -> List[vProcess]:
        """return the list of processes running in the container."""
        return self._processes

    @property
    def requests(self) -> List[vRequest]:
        """return the list of requests that the container has served."""
        return self._requests

    @property
    def deamon(self):
        """return the deamon of the container."""
        return self._deamon

    @property
    def schedulable(self) -> bool:
        """return True if the container is schedulable ( all volumes are attached successfully ), otherwise return False."""
        if all([volume.allocated for volume in self.volumes]):
            return True
        else:
            return False

    @property
    def cordon(self) -> bool:
        """return True if the container is cordon, otherwise return False."""
        return CORDON in self.status
