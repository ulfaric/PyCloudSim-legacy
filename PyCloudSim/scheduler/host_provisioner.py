from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Akatosh import Actor

from ..core import simulation
from ..priority import *
from ..status import *

if TYPE_CHECKING:
    from ..entity import vHost


class HostProvisioner:
    _power_saving: bool
    _evaluation_interval: Union[int, float]

    def __init__(
        self, power_saving: bool = True, evaluation_interval: Union[int, float] = 1
    ) -> None:
        """Host provisioner.

        Args:
            power_saving (bool, optional): set to true for power saving, that the host will be powered off if no container or volume is being hosted. Defaults to True.
            evaluation_interval (Union[int, float], optional): the interval for the host provisioner to check on the host. Defaults to 1.
        """
        self._power_saving = power_saving
        if evaluation_interval <= 0:
            raise ValueError(
                "Host privisioner evaluation delay must be greater than 0."
            )
        self._evaluation_interval = evaluation_interval
        simulation._host_privisioner = self

    def privision(self, host: vHost):
        """Provision a host."""
        def _evaluation():
            if host.powered_on:
                if len(host.containers) == 0:
                    host.power_off()
                else:
                    Actor(
                        at=simulation.now + self.evaluation_interval,
                        action=_evaluation,
                        label="Host Privisioning Evaluation",
                        priority=HOST_EVALUATION,
                    )

        if host.privisioned:
            return
        host._privisioned = True
        host.power_on()
        simulation.container_scheduler.schedule()
        simulation.volume_allocator.allocate()
        if self.power_saving:
            Actor(
                at=simulation.now + self.evaluation_interval,
                action=_evaluation,
                label="Host Privisioning Evaluation",
                priority=HOST_EVALUATION,
            )

    @property
    def power_saving(self) -> bool:
        """return true if power saving is enabled."""
        return self._power_saving

    @property
    def evaluation_interval(self) -> Union[int, float]:
        """return the evaluation interval."""
        return self._evaluation_interval
