from __future__ import annotations
from math import inf
from typing import List, Union, Optional, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
from uuid import uuid4

from Akatosh import Actor
from randomname import get_name

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *

if TYPE_CHECKING:
    from .v_nic import vNIC
    from .v_packet import vPacket
    from .v_process import vProcess


class Entity(ABC):
    _label: str
    _created_at: float
    _started_at: float
    _terminated_at: float
    _status: List[str]

    def __init__(
        self,
        label: Optional[str] = None,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
    ):
        """The base class for all simulated entity

        Args:
            label (Optional[str], optional): short description of the entity. Defaults to None.
            at (Union[int, float, Callable], optional): when the entity should be created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the entity must be created after. Defaults to None.
        """
        self._id = uuid4().int
        self._label = label if label else get_name()
        self._created_at = float()
        self._started_at = float()
        self._terminated_at = float()
        self._status = list()

        self._on_creation: Callable = lambda: None
        self._on_termination: Callable = lambda: None

        self._after = None
        if isinstance(after, list):
            self._after = [entity.terminator for entity in after]
        elif after is not None:
            self._after = after.terminator

        self._creator = Actor(
            at=at,
            after=self.after,
            action=self.creation,
            label=f"{self.__class__.__name__} {self.label} creation",
            priority=CREATION,
        )

        self._terminator = Actor(
            at=inf,
            action=self.__terminate,
            label=f"{self.__class__.__name__} {self.label} termination",
            active=False,
            priority=TERMINATION,
        )

    @abstractmethod
    def creation(self):
        """Creatation process of the entity."""
        self._created_at = simulation.now
        self.status.append(CREATED)
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is created."
        )
        self.on_creation()

    @abstractmethod
    def termination(self):
        """Termination process of the entity."""
        pass

    def __terminate(self):
        if self.terminated:
            return
        LOGGER.info(
            f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is terminated."
        )
        self._terminated_at = simulation.now
        self.status.append(TERMINATED)
        self.termination()
        self.on_termination()

    def terminate(self):
        """Terminate the entity."""
        if not self.created:
            raise RuntimeError(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is not created yet."
            )
        self.terminator.activate()

    @property
    def id(self) -> int:
        """The id of the entity."""
        return self._id

    @property
    def label(self) -> str:
        """The label of the entity."""
        return self._label

    @property
    def created_at(self) -> float:
        """The time when the entity is created."""
        return self._created_at

    @property
    def started_at(self) -> float:
        """The time when the entity is started."""
        return self._started_at

    @property
    def terminated_at(self) -> float:
        """The time when the entity is terminated."""
        return self._terminated_at

    @property
    def status(self) -> List[str]:
        """The status of the entity."""
        return self._status

    @property
    def created(self) -> bool:
        """Return True if the entity is created."""
        return CREATED in self._status

    @property
    def started(self) -> bool:
        """Return True if the entity is started."""
        return STARTED in self._status

    @property
    def terminated(self) -> bool:
        """Return True if the entity is terminated."""
        return TERMINATED in self._status

    @property
    def creator(self) -> Actor:
        """The creator of the entity."""
        return self._creator

    @property
    def terminator(self) -> Actor:
        """The terminator of the entity."""
        return self._terminator

    @property
    def after(self) -> Actor | List[Actor] | None:
        """The other enity that this entity must be created after."""
        return self._after

    @property
    def on_creation(self) -> Callable:
        """Callback function on creation process"""
        return self._on_creation

    @on_creation.setter
    def on_creation(self, func: Callable):
        self._on_creation = func

    @property
    def on_termination(self) -> Callable:
        """Callback function on termination process"""
        return self._on_termination

    @on_termination.setter
    def on_termination(self, func: Callable):
        self._on_termination = func
