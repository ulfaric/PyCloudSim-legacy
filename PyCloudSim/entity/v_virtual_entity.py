from __future__ import annotations
from typing import List, Union, Optional, Callable
from abc import ABC

from ..core import simulation
from ..status import *
from ..priority import *
from ..logger import LOGGER
from .v_entity import Entity


class VirtualEntity(Entity, ABC):
    _initiated_at: float
    _scheduled_at: float
    _completed_at: float

    def __init__(
        self,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        super().__init__(at=at, after=after, label=label)
        self._scheduled_at = float()
        self._completed_at = float()

    def creation(self):
        return super().creation()

    @property
    def initiated_at(self) -> float:
        return self._initiated_at

    @property
    def scheduled_at(self) -> float:
        return self._scheduled_at

    @property
    def initiated(self) -> bool:
        return INITIATED in self._status

    @property
    def completed_at(self) -> float:
        return self._completed_at

    @property
    def scheduled(self) -> bool:
        return SCHEDULED in self._status

    @property
    def completed(self) -> bool:
        return COMPLETED in self._status

    @property
    def failed(self) -> bool:
        return FAILED in self._status
