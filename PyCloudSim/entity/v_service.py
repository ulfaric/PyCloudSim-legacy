from __future__ import annotations
from random import choice
from typing import List, Callable, Any, TYPE_CHECKING
from abc import ABC, abstractmethod

from Akatosh import Actor
from matplotlib import container

from PyCloudSim.core import simulation
from PyCloudSim.entity.v_entity import Entity

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_container import vContainer
from .v_volume import vVolume
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity

if TYPE_CHECKING:
    from .v_microservice import vMicroservice


class vService(VirtualEntity, ABC):
    def __init__(
        self,
        ms: vMicroservice,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        """Base class for virtual services.

        Args:
            ms (vMicroservice): the associated vMicroservice.
            ports (List[int], optional): the exposed ports for vContainers. Defaults to [].
            at (int | float | Callable[..., Any], optional): same as entity. Defaults to simulation.now.
            after (Entity | List[Entity] | None, optional): same as entity. Defaults to None.
            label (str | None, optional): same as entity. Defaults to None.
        """        
        super().__init__(at, after, label)
        # assign the microservice
        self._ms_id = ms.id
        # assign the ip address
        self._ip_address = choice(simulation.virtual_network_ips)
        simulation.virtual_network_ips.remove(self.ip_address)
        # ports
        self._ports = ports

    def creation(self):
        """Creation process of a vService."""
        return super().creation()

    def termination(self):
        """Termination process of a vService."""
        return super().termination()

    @abstractmethod
    def loadbalancer(self) -> vContainer:
        """The loadbalancer of the vService. Can be implemented by the developer."""
        pass

    @property
    def ms_id(self):
        """The id of the associated vMicroservice."""
        return self._ms_id

    @property
    def ip_address(self):
        """The ip address of the vService."""
        return self._ip_address

    @property
    def ms(self):
        """The associated vMicroservice."""
        for ms in simulation.MICROSERVICES:
            if ms.id == self.ms_id:
                return ms
        raise Exception(
            f"Can not find associated vMicroservice for vService {self.id}."
        )


class vServiceRoundRobin(vService):
    """vService with round robin loadbalancer."""
    def __init__(
        self,
        ms: vMicroservice,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        super().__init__(ms, ports, at, after, label)
        self._container_pointer = 0

    def loadbalancer(self):
        if all(container.scheduled == False for container in self.ms.containers):
            return None
        elif all(container.cordon == True for container in self.ms.containers):
            return None
        elif all(container.terminated == True for container in self.ms.containers):
            return None
        else:
            while True:
                container = self.ms.containers[self.container_pointer]
                self._container_pointer = (self.container_pointer + 1) % len(
                    self.ms.containers
                )
                if container.scheduled:
                    return container

    @property
    def container_pointer(self):
        return self._container_pointer


class vServiceBestFit(vService):
    """vService with best fit loadbalancer."""
    def __init__(
        self,
        ms: vMicroservice,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        super().__init__(ms, ports, at, after, label)

    def loadbalancer(self):
        self.ms.containers.sort(key=lambda x: x.ram.utilization)
        self.ms.containers.sort(key=lambda x: x.cpu.utilization)
        for container in self.ms.containers:
            if container.scheduled and not container.cordon and not container.terminated:
                return container
        return None


class vServiceWorstFit(vService):
    """vService with worst fit loadbalancer."""
    def __init__(
        self,
        ms: vMicroservice,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        super().__init__(ms, ports, at, after, label)

    def loadbalancer(self):
        self.ms.containers.sort(key=lambda x: x.ram.utilization)
        self.ms.containers.sort(key=lambda x: x.cpu.utilization)

        for container in reversed(self.ms.containers):
            if container.scheduled and not container.cordon and not container.terminated:
                return container
        return None


class vServiceRandom(vService):
    """vService with random loadbalancer."""
    def __init__(
        self,
        ms: vMicroservice,
        ports: List[int] = [],
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        super().__init__(ms, ports, at, after, label)

    def loadbalancer(self):
        if all(container.scheduled == False for container in self.ms.containers):
            return None
        elif all(container.cordon == True for container in self.ms.containers):
            return None
        elif all(container.terminated == True for container in self.ms.containers):
            return None
        else:
            while True:
                container = choice(self.ms.containers)
                if container.scheduled:
                    return container
