from __future__ import annotations
import random
from re import T
from typing import TYPE_CHECKING, Union
from abc import ABC, abstractmethod

from Akatosh import Actor

from PyCloudSim.entity import vContainer, vHost

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *


if TYPE_CHECKING:
    from ..entity import vHost, vContainer


class ContainerScheduler(ABC):
    __host_affinity: bool

    def __init__(
        self,
        host_affinity: bool = False,
    ) -> None:
        """Base class for container schedulers.

        Args:
            host_affinity (bool, optional): set to true for host affinity scheduling, that the host and container must have the same taint. Defaults to False.
        """        
        self._host_affinity = host_affinity
        self._active_process: Actor = None  # type: ignore
        simulation._container_scheduler = self

    @abstractmethod
    def find_host(self, container: vContainer) -> Union[vHost, None]:
        """Abstract function to be implemented with your specific container scheduling algorithm."""
        pass

    def schedule(self):
        """Event function to be called by the simulation engine to schedule containers. find_host() is called automatically by this function."""
        def _schedule():
            self._active_process = None  # type: ignore
            for container in simulation.CONTAINERS:
                if (
                    container.scheduled
                    or container.terminated
                    or not container.schedulable
                ):
                    continue

                if candidate_host := self.find_host(container):
                    candidate_host.allocate_container(container)

                if not container.scheduled:
                    LOGGER.info(
                        f"{simulation.now:0.2f}\tvContainer {container.label} can not be shceduled, privisioning new vHost if possible."
                    )
                    if self.host_affinity:
                        for host in simulation.HOSTS:
                            if host.taint == container.taint:
                                simulation.host_privisioner.privision(host)

                    else:
                        for host in simulation.HOSTS:
                            if host.powered_off:
                                simulation.host_privisioner.privision(host)

        if self.active_process is None:
            self._active_process = Actor(
                at=simulation.now,
                action=_schedule,
                label=f"vContainer Scheduling",
                priority=CONTAINER_SCHEDULER,
            )

    @property
    def host_affinity(self) -> bool:
        """returns True if host affinity is enabled, False otherwise."""
        return self._host_affinity

    @property
    def active_process(self) -> Actor:
        """returns the active process of the scheduler."""
        return self._active_process


class ContainerSchedulerBestfit(ContainerScheduler):
    """Bestfit container scheduler, that finds the fullest host for the container based on the available resources of the host.
    """
    def find_host(self, container: vContainer) -> vHost | None:
        if self._host_affinity:
            candidate_host = [host for host in simulation.HOSTS if host.taint == container.taint and host.powered_on]
            candidate_host.sort(key=lambda host: host.ram.utilization)
            candidate_host.sort(key=lambda host: host.cpu.utilization)
            for host in candidate_host:
                if (
                    host.cpu_reservor.available_quantity >= container.cpu_request
                    and host.ram_reservor.available_quantity
                    >= container.ram_request
                    and host.rom.available_quantity >= container.image_size
                ):
                    LOGGER.debug(
                        f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu.availablity} CPU, {host.ram.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                    )
                    return host
        else:
            simulation.HOSTS.sort(key=lambda host: host.ram.utilization)
            simulation.HOSTS.sort(key=lambda host: host.cpu.utilization)
            for host in simulation.HOSTS:
                if host.powered_on:
                    if (
                        host.cpu_reservor.available_quantity >= container.cpu_request
                        and host.ram_reservor.available_quantity
                        >= container.ram_request
                        and host.rom.available_quantity >= container.image_size
                    ):
                        LOGGER.debug(
                            f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu_reservor.available_quantity} CPU, {host.ram_reservor.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                        )
                        return host

        return None

class ContainerSchedulerWorstfit(ContainerScheduler):
    """Worstfit container scheduler, that finds the most empty host for the container based on the available resources of the host.
    """
    def find_host(self, container: vContainer) -> vHost | None:
        if self._host_affinity:
            candidate_host = [host for host in simulation.HOSTS if host.taint == container.taint and host.powered_on]
            candidate_host.sort(key=lambda host: host.ram.utilization, reverse=True)
            candidate_host.sort(key=lambda host: host.cpu.utilization, reverse=True)
            for host in candidate_host:
                if (
                    host.cpu_reservor.available_quantity >= container.cpu_request
                    and host.ram_reservor.available_quantity
                    >= container.ram_request
                    and host.rom.available_quantity >= container.image_size
                ):
                    LOGGER.debug(
                        f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu.availablity} CPU, {host.ram.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                    )
                    return host
        else:
            simulation.HOSTS.sort(key=lambda host: host.ram.utilization, reverse=True)
            simulation.HOSTS.sort(key=lambda host: host.cpu.utilization, reverse=True)
            for host in simulation.HOSTS:
                if host.powered_on:
                    if (
                        host.cpu_reservor.available_quantity >= container.cpu_request
                        and host.ram_reservor.available_quantity
                        >= container.ram_request
                        and host.rom.available_quantity >= container.image_size
                    ):
                        LOGGER.debug(
                            f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu_reservor.available_quantity} CPU, {host.ram_reservor.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                        )
                        return host

        return None
    
class ContainerSchedulerRandom(ContainerScheduler):
    """Worstfit container scheduler, that finds the most empty host for the container based on the available resources of the host.
    """
    def find_host(self, container: vContainer) -> vHost | None:
        if self._host_affinity:
            candidate_host = [host for host in simulation.HOSTS if host.taint == container.taint and host.powered_on]
            random.shuffle(candidate_host)
            for host in candidate_host:
                if (
                    host.cpu_reservor.available_quantity >= container.cpu_request
                    and host.ram_reservor.available_quantity
                    >= container.ram_request
                    and host.rom.available_quantity >= container.image_size
                ):
                    LOGGER.debug(
                        f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu.availablity} CPU, {host.ram.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                    )
                    return host
        else:
            random.shuffle(simulation.HOSTS)
            for host in simulation.HOSTS:
                if host.powered_on:
                    if (
                        host.cpu_reservor.available_quantity >= container.cpu_request
                        and host.ram_reservor.available_quantity
                        >= container.ram_request
                        and host.rom.available_quantity >= container.image_size
                    ):
                        LOGGER.debug(
                            f"{simulation.now:0.2f}\tFound vHost {host.label} {host.cpu_reservor.available_quantity} CPU, {host.ram_reservor.available_quantity} RAM, {host.rom.available_quantity} ROM for vContainer {container.label} {container.cpu_request} CPU, {container.ram_request} RAM, {container.image_size} ROM"
                        )
                        return host

        return None