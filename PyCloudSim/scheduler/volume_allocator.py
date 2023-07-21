from __future__ import annotations
from typing import TYPE_CHECKING, Union
from abc import ABC, abstractmethod
import warnings

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *


if TYPE_CHECKING:
    from ..entity import vHost, vVolume


class VolumeAllocator:
    _host_affinity: bool

    def __init__(
        self,
        host_affinity: bool = False,
    ):
        """volume allocator.

        Args:
            host_affinity (bool, optional): set to true to enable volume allocator. Defaults to False.
        """        
        self._host_affinity = host_affinity
        self._active_process: Actor = None  # type: ignore
        simulation._volume_allocator = self

    def allocate(self):
        """Allocate the volume."""
        def _allocate():
            self._active_process = None  # type: ignore
            for volume in simulation.VOLUMES:
                if volume.allocated or volume.terminated:
                    continue

                if self.host_affinity:
                    for host in simulation.HOSTS:
                        if (
                            host.taint == volume.taint
                            and host.powered_on
                            and host.rom.available_quantity >= volume.size
                        ):
                            host.allocate_volume(volume)
                            volume._allocated = True
                            self._active_process = None  # type: ignore
                        break

                else:
                    for host in simulation.HOSTS:
                        if (
                            host.powered_on
                            and host.rom.available_quantity >= volume.size
                        ):
                            host.allocate_volume(volume)
                            volume._allocated = True
                            self._active_process = None  # type: ignore
                        break

                if not volume.allocated:
                    LOGGER.info(
                        f"{simulation.now:0.2f}:\tvVolume {volume.label} can not be allocated, privisioning new vHost if possible."
                    )
                    if self.host_affinity:
                        for host in simulation.HOSTS:
                            if host.taint == volume.taint:
                                simulation.host_privisioner.privision(host)
                    else:
                        for host in simulation.HOSTS:
                            if host.powered_off:
                                simulation.host_privisioner.privision(host)

        if self.active_process is None:
            self._active_process = Actor(
                at=simulation.now,
                action=_allocate,
                label=f"vVolume Allocate",
                priority=VOLUME_ALLOCATOR,
            )

    @property
    def host_affinity(self) -> bool:
        """Return the """
        return self._host_affinity

    @property
    def active_process(self) -> Actor:
        """return the current active scheduler process."""
        return self._active_process
