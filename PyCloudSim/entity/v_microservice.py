from __future__ import annotations
from math import e
from random import choice
from re import L
from typing import List, Type, Union, Optional, Callable, Tuple, Any
from abc import ABC, abstractmethod

from Akatosh import Actor
from matplotlib import container, scale

from PyCloudSim.core import simulation
from PyCloudSim.entity.v_entity import Entity
from PyCloudSim.entity.v_service import (
    Callable,
    Entity,
    List,
    simulation,
    vService,
    vServiceBestFit,
)

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_container import vContainer
from .v_volume import vVolume
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity
from .v_service import *


class vMicroservice(VirtualEntity, ABC):
    def __init__(
        self,
        cpu: int,
        cpu_limit: int,
        ram: int,
        ram_limit: int,
        image_size: int,
        volumes: Optional[List[Tuple[str, str, int, bool]]] = None,
        taint: Optional[str] = None,
        deamon: bool = False,
        min_num_containers: int = 1,
        max_num_containers: int = 3,
        evaluation_interval: float = 0.01,
        service: Type[vService] = vServiceBestFit,
        ports: List[int] = [],
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a virtual microservice.

        Args:
            cpu (int): the requested CPU time.
            cpu_limit (int): the limited CPU time.
            ram (int): the requested RAM in MiB.
            ram_limit (int): the limited RAM in MiB.
            image_size (int): the image size in MiB of the microservice container instance.
            volumes (Optional[List[Tuple[str, str, int, bool]]], optional): The volumes that are attached to each container instance, (name, path, size in MiB, retain or not). Defaults to None.
            taint (Optional[str], optional): the taint of the microservice, used in scheduling. Defaults to None.
            deamon (bool, optional): set true for create deamon process for container instance. Defaults to False.
            min_num_containers (int, optional): minimum number of container instances. Defaults to 1.
            max_num_containers (int, optional): maximum number of container instances. Defaults to 3.
            evaluation_interval (float, optional): the interval for horizontal scaler to check on the microservice. Defaults to 0.01.
            service (Type[vService], optional): the service for this microservice, will determine the load balancing method. Defaults to vServiceBestFit.
            ports (List[int], optional): the port that are exposed. Defaults to [].
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(at, after, label)

        self._cpu = cpu
        self._cpu_limit = cpu_limit
        self._ram = ram
        self._ram_limit = ram_limit
        self._image_size = image_size
        self._volumes = volumes
        self._taint = taint
        self._volumes = volumes
        self._taint = taint
        self._deamon = deamon

        self._min_num_containers = min_num_containers
        self._containers = list()
        for i in range(min_num_containers):
            container = vContainer(
                cpu=cpu,
                cpu_limit=cpu_limit,
                ram=ram,
                ram_limit=ram_limit,
                image_size=image_size,
                volumes=volumes,
                taint=taint,
                label=f"{self.label}-{i}",
                deamon=self.deamon,
            )
            container._microservice_id = self.id
            self.containers.append(container)
        self._max_num_containers = max_num_containers
        self._service = service(ms=self, ports=ports, label=f"{self.label}-service")
        self._evaluator = Actor(
            at=simulation.now,
            step=evaluation_interval,
            action=self.evaluate,
            label=f"vMicroservice {self.label} Evaluator",
        )
        simulation.MICROSERVICES.append(self)

    def termination(self):
        """Termination process of the virtual microservice."""
        super().termination()
        self.service.terminate()
        for container in self.containers:
            container.terminate()

    def evaluate(self):
        """Evaluate the status of the virtual microservice, and trigger scaling up or down."""
        scheduled_container = [
            container for container in self.containers if container.scheduled
        ]
        if len(scheduled_container) >= self.min_num_containers:
            self.status.append(READY)
            LOGGER.info(f"{simulation.now:0.2f}:\tvMicroservice {self.label} is ready. {self.cpu_usage_in_past(0.01)} CPU, {self.ram_usage_in_past(0.01)} RAM.")
        else:
            if self.ready:
                self.status.remove(READY)
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvMicroservice {self.label} is not ready, {len(scheduled_container)}/{self.min_num_containers}."
            )

        for sfc in simulation.SFCS:
            if not sfc.ready:
                sfc.evaluate()

        if self.scale_up_triggered():
            if (
                len(self.containers) < self.max_num_containers
                and len(
                    [
                        container
                        for container in self.containers
                        if not container.scheduled
                    ]
                )
                == 0
            ):
                new_container = vContainer(
                    cpu=self.cpu,
                    cpu_limit=self.cpu_limit,
                    ram=self.ram,
                    ram_limit=self.ram_limit,
                    image_size=self.image_size,
                    volumes=self.volumes,
                    taint=self.taint,
                    label=f"{self.label}-{len(self.containers)}",
                    deamon=self.deamon,
                )
                new_container._microservice_id = self.id
                self.containers.append(new_container)
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvMicroservice {self.label} scaled up one vContainer {new_container.label}."
                )
        elif self.scale_down_triggered():
            if len(self.containers) > self.min_num_containers:
                self.containers.sort(key=lambda container: len(container.processes))
                if len(self.containers[0].requests) == 0:
                    self.containers[0].terminate()
                    LOGGER.info(
                        f"{simulation.now:0.2f}:\tvMicroservice {self.label} scaled down one vContainer {self.containers[0].label}."
                    )
                else:
                    if (
                        len(
                            [
                                container
                                for container in self.containers
                                if container.status == CORDON
                            ]
                        )
                        == 0
                    ):
                        self.containers[0].status.append(CORDON)
                    LOGGER.info(
                        f"{simulation.now:0.2f}:\tvContainer {self.containers[0].label} is cordoned."
                    )

    def recover(
        self, container: vContainer, detached_volumes: Optional[List[vVolume]] = None
    ):
        """Recover a failed container instance."""
        def _recover():
            # find non-retained volumes to recover
            volumes_to_recover = list()
            if self.volumes is not None and detached_volumes is not None:
                for volume in detached_volumes:
                    for v_definitions in self.volumes:
                        if (
                            volume.tag == v_definitions[0]
                            and volume.path == v_definitions[1]
                        ):
                            continue
                        else:
                            volumes_to_recover.append(v_definitions)
            # recover container
            recovered_container = vContainer(
                cpu=self.cpu,
                cpu_limit=self.cpu_limit,
                ram=self.ram,
                ram_limit=self.ram_limit,
                image_size=self.image_size,
                volumes=volumes_to_recover,
                taint=self.taint,
                label=container.label,
                deamon=self.deamon,
            )
            recovered_container._microservice_id = self.id
            if detached_volumes is not None:
                for volume in detached_volumes:
                    volume.attach(recovered_container)
            self._containers.append(recovered_container)
            LOGGER.info(
                f"{simulation.now:0.2f}:\tvMicroservice {self.label} recovered one failed containers."
            )

        if not self.terminated:
            Actor(
                at=simulation.now,
                action=_recover,
                label=f"vMicroservice {self.label} Recover",
                priority=CREATION,
            )

    @abstractmethod
    def scale_up_triggered(self) -> bool:
        """For developer to implement the scaling up trigger condition."""
        pass

    @abstractmethod
    def scale_down_triggered(self) -> bool:
        """For developer to implement the scaling down trigger condition."""
        pass

    @property
    def containers(self) -> List[vContainer]:
        """The container instances of the virtual microservice."""
        return self._containers

    @property
    def cpu(self) -> int:
        """The requested CPU time of the virtual microservice."""
        return self._cpu

    @property
    def cpu_limit(self) -> int:
        """The limited CPU time of the virtual microservice."""
        return self._cpu_limit

    @property
    def ram(self) -> int:
        """The requested RAM in MiB of the virtual microservice."""
        return self._ram

    @property
    def ram_limit(self) -> int:
        """The limited RAM in MiB of the virtual microservice."""
        return self._ram_limit

    @property
    def image_size(self) -> int:
        """The image size in MiB of the microservice container instance."""
        return self._image_size

    @property
    def volumes(self) -> Optional[List[Tuple[str, str, int, bool]]]:
        """The volumes that are attached to each container instance, (name, path, size in MiB, retain or not)."""
        return self._volumes

    @property
    def taint(self) -> Optional[str]:
        """The taint of the microservice, used in scheduling."""
        return self._taint

    @property
    def min_num_containers(self) -> int:
        """The minimum number of container instances."""
        return self._min_num_containers

    @property
    def max_num_containers(self) -> int:
        """The maximum number of container instances."""
        return self._max_num_containers

    @property
    def ready(self) -> bool:
        """Return True if the virtual microservice is ready."""
        return READY in self.status

    @property
    def cpu_usage(self) -> float:
        """The CPU utilization of the virtual microservice."""
        return sum([container.cpu.utilization for container in self.containers]) / len(
            self.containers
        )

    def cpu_usage_in_past(self, interval: float) -> float:
        """The CPU utilization of the virtual microservice in the past interval."""
        return sum(
            [
                container.cpu.utilization_in_past(interval)
                for container in self.containers
                if container.scheduled
            ]
        ) / len(self.containers)

    @property
    def ram_usage(self) -> float:
        """The RAM utilization of the virtual microservice."""
        return sum([container.ram.utilization for container in self.containers]) / len(
            self.containers
        )

    def ram_usage_in_past(self, interval: float) -> float:
        """The RAM utilization of the virtual microservice in the past interval."""
        return sum(
            [
                container.ram.utilization_in_past(interval)
                for container in self.containers
                if container.scheduled
            ]
        ) / len(self.containers)

    @property
    def deamon(self) -> bool:
        """Return True if the virtual microservice has a deamon process."""
        return self._deamon

    @property
    def service(self) -> vService:
        """Return the service of the virtual microservice."""
        return self._service


class vMicroserviceDeafult(vMicroservice):
    def __init__(
        self,
        cpu: int,
        cpu_limit: int,
        ram: int,
        ram_limit: int,
        image_size: int,
        volumes: List[Tuple[str, str, int, bool]] | None = None,
        taint: str | None = None,
        deamon: bool = False,
        min_num_containers: int = 1,
        max_num_containers: int = 3,
        evaluation_interval: float = 0.01,
        cpu_lower_bound: float = 0.2,
        cpu_upper_bound: float = 0.8,
        ram_lower_bound: float = 0.2,
        ram_upper_bound: float = 0.8,
        cool_down_period: float = 5,
        service: Type[vService] = vServiceBestFit,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        """Create a virtual microservice with default horizontal scaler."""
        super().__init__(
            cpu,
            cpu_limit,
            ram,
            ram_limit,
            image_size,
            volumes,
            taint,
            deamon,
            min_num_containers,
            max_num_containers,
            evaluation_interval,
            service,
            ports,
            at,
            after,
            label,
        )
        self._cpu_lower_bound = cpu_lower_bound
        self._cpu_upper_bound = cpu_upper_bound
        self._ram_lower_bound = ram_lower_bound
        self._ram_upper_bound = ram_upper_bound
        self._cool_down_period = cool_down_period

    def scale_up_triggered(self) -> bool:
        """Default scaling up trigger condition."""
        if (
            self.cpu_usage > self.cpu_upper_bound
            or self.ram_usage > self.ram_upper_bound
        ):
            return True
        else:
            return False

    def scale_down_triggered(self) -> bool:
        """Default scaling down trigger condition."""
        if (
            self.cpu_usage < self.cpu_lower_bound
            and self.ram_usage < self.ram_lower_bound
        ):
            return True
        else:
            return False

    @property
    def cpu_lower_bound(self) -> float:
        """The lower bound of CPU utilization."""
        return self._cpu_lower_bound

    @property
    def cpu_upper_bound(self) -> float:
        """The upper bound of CPU utilization."""
        return self._cpu_upper_bound

    @property
    def ram_lower_bound(self) -> float:
        """The lower bound of RAM utilization."""
        return self._ram_lower_bound

    @property
    def ram_upper_bound(self) -> float:
        """The upper bound of RAM utilization."""
        return self._ram_upper_bound

    @property
    def cool_down_period(self) -> float:
        """The cool down period of the virtual microservice, no scaling operation will happen during cool down period."""
        return self._cool_down_period
