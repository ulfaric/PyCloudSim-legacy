from __future__ import annotations
from typing import Union, Optional, Callable, List, TYPE_CHECKING
import warnings
from bitmath import MiB

from Akatosh import Actor

from .v_entity import Entity
from .v_virtual_entity import VirtualEntity
from ..core import simulation
from ..priority import *
from ..logger import LOGGER

if TYPE_CHECKING:
    from .v_container import vContainer
    from .v_host import vHost


class vVolume(VirtualEntity):
    def __init__(
        self,
        tag: Optional[str] = None,
        path: Optional[str] = None,
        size: int = 100,
        retain: bool = False,
        taint: Optional[str] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vVolume.

        Args:
            tag (Optional[str], optional): the tag of the vVolume. Defaults to None.
            path (Optional[str], optional): the path of the vVolume. Defaults to None.
            size (int, optional): the sime of the vVolume in MiB. Defaults to 100.
            retain (bool, optional): set true if the vVolume will be retained. Defaults to False.
            taint (Optional[str], optional): the taint of the vVolume. Defaults to None.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """        
        super().__init__(at, after, label)
        self._container_id = int()
        self._host_id = int()
        self._tag = tag or str()
        self._path = path or str()
        self._size = MiB(size)
        self._retain = retain
        self._taint = taint or str()
        self._attached = False
        self._allocated = False
        self._on_creation = simulation.volume_allocator.allocate
        simulation.VOLUMES.append(self)

    def termination(self):
        """The termination of a vVolume."""
        super().termination()
        if self.allocated:
            self.host.rom.release(self)
        simulation.volume_allocator.allocate()

    def attach(self, container: vContainer):
        """Attach the vVolume to a vContainer."""
        def _attach():
            self._container_id = container.id
            self._attached = True
            LOGGER.info(f"{simulation.now:0.2f}:\tVirtual Volume {self.label} is attached to vContainer {container.label}.")

        Actor(
            action=_attach,
            at=simulation.now,
            label=f"vVolume {self.label} Attach",
            priority=VOLUME_ATACH,
        )

    def detach(self):
        """Detach the vVolume from a vContainer."""
        def _detach():
            LOGGER.info(f"{simulation.now:0.2f}:\tVirtual Volume {self.label} is detached from vContainer {self.container.label}.")
            self._container_id = int()
            self._attached = False

        Actor(
            action=_detach,
            at=simulation.now,
            label=f"vVolume {self.label} Detach",
            priority=VOLUME_DETACH,
        )

    @property
    def container_id(self) -> int:
        """The id of the vContainer that the vVolume is attached to."""
        return self._container_id

    @property
    def container(self) -> vContainer:
        """The vContainer that the vVolume is attached to."""
        for container in simulation.CONTAINERS:
            if container.id == self.container_id:
                return container
        warnings.warn(f"Virtual Volume {self.label} is detached.")
        return None  # type: ignore

    @property
    def host_id(self) -> int:
        """The id of the vHost that the vVolume is allocated on."""
        return self._host_id

    @property
    def host(self) -> vHost:
        """The vHost that the vVolume is allocated on."""
        for host in simulation.HOSTS:
            if host.id == self.host_id:
                return host
        raise RuntimeError(f"Virtual Volume {self.label} is not allocated on any host.")

    @property
    def tag(self) -> str:
        """The tag of the vVolume."""
        return self._tag

    @property
    def path(self) -> str:
        """The path of the vVolume."""
        return self._path

    @property
    def size(self) -> Union[int, float]:
        """The size of the vVolume in MiB."""
        return self._size.bytes

    @property
    def retain(self) -> bool:
        """Return true if the vVolume is retained."""
        return self._retain
    
    @property
    def taint(self) -> str:
        """The taint of the vVolume."""
        return self._taint

    @property
    def attached(self) -> bool:
        """Check if the vVolume is attached to a vContainer."""
        return self._attached
    
    @property
    def allocated(self) -> bool:
        """Check if the vVolume is allocated on a vHost."""
        return self._allocated