from __future__ import annotations

from math import inf
from typing import TYPE_CHECKING, Callable, List, Optional, Union

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..priority import *
from ..status import *
from .v_cpu_core import vCPUCore
from .v_entity import Entity
from .v_physical_component import PhysicalComponent

if TYPE_CHECKING:
    from .v_process import vProcess


class vCPU(PhysicalComponent):
    _cpu_cores: List[vCPUCore]
    _processes: List[vProcess]

    def __init__(
        self,
        ipc: Union[int, float],
        frequency: Union[int, float],
        num_cores: int,
        tdp: Union[int, float] = 50,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Creates a new vCPU.

        Args:
            ipc (Union[int, float]): instructions per cycle.
            frequency (Union[int, float]): the frequency of cpu core.
            num_cores (int): the number of cores in the cpu.
            tdp (Union[int, float], optional): the TDP, aka power consumption of the cpu. Defaults to 50W.
            at (Union[int, float, Callable], optional): when the cpu should be created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the entity that must be terminated before the cpu can be created. Defaults to None.
            label (Optional[str], optional): short description of the cpu. Defaults to None.
        """
        super().__init__(at, after, label)
        self._ipc = ipc
        self._frequency = frequency * 1000000
        self._num_cores = num_cores
        cpu_cores = [
            vCPUCore(
                ipc=self.ipc,
                frequency=self.frequency,
                cpu=self,
                label=f"{self.label}-Core-{i}",
            )
            for i in range(num_cores)
        ]
        self._cpu_cores = cpu_cores
        self._tdp = tdp
        self._processes = list()
        self._process_scheduler: Actor = None  # type: ignore
        simulation.CPUS.append(self)

    def creation(self):
        """Creates the cpu."""
        return super().creation()

    def termination(self):
        """Terminates the cpu."""
        return super().termination()

    def _power_on(self):
        """Power on the cpu and all its cores."""
        super()._power_on()
        for core in self.cpu_cores:
            core.power_on()

    def _power_off(self):
        """Power off the cpu and all its cores."""
        super()._power_off()
        for core in self.cpu_cores:
            core.power_off()

    def cache_process(self, process: vProcess):
        """Cache a process in the cpu and call schedule_process()."""
        if not process.cached:
            self.processes.append(process)
            process._cpu_id = self.id
            process.status.append(CACHED)
            self.schedule_process()

    def schedule_process(self):
        """shcedule processes in the cpu queue."""

        def _schedule_process():
            LOGGER.debug(
                f"{simulation.now:0.2f}:\tvCPU {self.label} is scheduling ... {len(self.processes)} processes"
            )
            self.processes.sort(key=lambda process: process.priority)
            for process in self.processes:
                # if not process.executing and not process.terminated:
                for core in self.cpu_cores:
                    remaining_to_schedule_instruction_length = (
                        process.remaining - process.current_scheduled_length
                    )
                    if process.__class__.__name__ == "vPacketHandler":
                        container_allowed_instruction_length = inf
                    else:
                        container_allowed_instruction_length = (
                            process.container.cpu.available_quantity  # type: ignore
                            / 1000
                            * core.capacity
                        )
                    schedulable_instruction_length = int(
                        min(
                            [
                                remaining_to_schedule_instruction_length,
                                container_allowed_instruction_length,
                                core.availablity,
                            ]
                        )
                    )
                    if schedulable_instruction_length > 0:
                        core.execute_process(process, schedulable_instruction_length)
                        process._current_scheduled_length += (
                            schedulable_instruction_length
                        )
                        scheduled_cpu_time = (
                            schedulable_instruction_length / core.capacity
                        ) * 1000

                        if process.__class__.__name__ != "vPacketHandler":
                            process.container.cpu.distribute(  # type: ignore
                                process, scheduled_cpu_time
                            )

            LOGGER.debug(
                f"{simulation.now:0.2f}:\tvCPU {self.label} scheduled all process within the queue."
            )

            self._process_scheduler = None  # type: ignore

        if self.process_scheduler is None:
            self._process_scheduler = Actor(
                at=simulation.now,
                action=_schedule_process,
                label=f"vCPU {self.label} Schedule vProcess",
                priority=CPU_SCHEDULE_PROCESS,
            )

    @property
    def ipc(self) -> Union[int, float]:
        """return the IPC of the cpu."""
        return self._ipc

    @property
    def frequency(self) -> Union[int, float]:
        """return the frequency of the cpu."""
        return self._frequency

    @property
    def num_cores(self) -> int:
        """return the number of cores of the cpu."""
        return self._num_cores

    @property
    def single_core_capacity(self) -> Union[int, float]:
        """return the single core capacity of the cpu."""
        return (self.ipc * self.frequency) / simulation.cpu_acceleration

    @property
    def cpu_cores(self) -> List[vCPUCore]:
        """return the cpu cores of the cpu."""
        return self._cpu_cores

    @property
    def capacity(self) -> Union[int, float]:
        """return the capacity of the cpu."""
        return sum([core.capacity for core in self.cpu_cores])

    @property
    def availablity(self) -> Union[int, float]:
        """return the availablity of the cpu."""
        return sum([core.availablity for core in self.cpu_cores])

    @property
    def utilization(self) -> Union[int, float]:
        """return the utilization of the cpu."""
        return (self.capacity - self.availablity) / self.capacity * 100

    def utilization_in_past(self, interval: Union[int, float]) -> Union[int, float]:
        """return the utilization of the cpu in the past interval."""
        return (
            sum(
                [
                    core.computational_power.utilization_in_past(interval)
                    for core in self.cpu_cores
                ]
            )
            / self.num_cores
        )

    @property
    def processes(self) -> List[vProcess]:
        """return the processes of the cpu."""
        return self._processes

    @property
    def process_scheduler(self) -> Actor:
        """return the process scheduler of the cpu, if it is runing at the moment."""
        return self._process_scheduler

    @property
    def tdp(self) -> Union[int, float]:
        """return the TDP of the cpu."""
        return self._tdp
