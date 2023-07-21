from __future__ import annotations
from math import inf
from typing import List, Union, Optional, Callable
from abc import ABC, abstractmethod

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity

class PhysicalComponent(Entity, ABC):
    _privisoned_at: float

    def __init__(
        self,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a physical component.

        Args:
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
            label (Optional[str], optional): same as entity. Defaults to None.
        """
        super().__init__(at=at, after=after, label=label)
        simulation.topology.add_node(self)

    @abstractmethod
    def _power_on(self):
        """Power on the physical component."""
        if self.powered_off:
            self.status.append(POWERED_ON)
            self.on_power_on()
            LOGGER.info(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is powered on."
            )

    def power_on(self):
        """Power on the physical component."""
        if self.powered_off:
            Actor(
                at=simulation.now,
                action=self._power_on,
                label=f"{self.__class__.__name__} {self.label} Power On.",
                priority=POWERING,
            )
            
    def on_power_on(self):
        """Callback function for when the physical component is powered on."""
        pass

    @abstractmethod
    def _power_off(self):
        """Power off the physical component."""
        if self.powered_on:
            self.status.remove(POWERED_ON)
            self.status.append(POWERED_OFF)
            self.on_power_off()
            LOGGER.info(
                f"{simulation.now:0.2f}:\t{self.__class__.__name__} {self.label} is powered off."
            )

    def power_off(self):
        """Power off the physical component."""
        if self.powered_on:
            Actor(
                at=simulation.now,
                action=self._power_off,
                label=f"{self.__class__.__name__} {self.label} Power Off.",
                priority=POWERING,
            )
            
    def on_power_off(self):
        """Callback function for when the physical component is powered off."""
        pass

    @property
    def powered_on(self) -> bool:
        """returns True if the physical component is powered on, False otherwise."""
        return POWERED_ON in self._status

    @property
    def powered_off(self) -> bool:
        """returns True if the physical component is powered off, False otherwise."""
        return POWERED_ON not in self._status