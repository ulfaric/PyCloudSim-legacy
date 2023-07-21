from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Union, Callable

from Akatosh import Resource, Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_physical_component import PhysicalComponent

if TYPE_CHECKING:
    from .v_process import vProcess
    from .v_host import vHost
    from .v_cpu import vCPU


class vCPUCore(PhysicalComponent):
    _ipc: Union[int, float]
    _frequency: Union[int, float]
    _computational_power: Resource
    _processes: List[vProcess]

    def __init__(
        self,
        ipc: Union[int, float],
        frequency: Union[int, float],
        cpu: vCPU,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Creates a new vCPUCore.

        Args:
            ipc (Union[int, float]): instructions per cycle.
            frequency (Union[int, float]): the frequency of cpu core.
            cpu (vCPU): the cpu that this core belongs to.
            at (Union[int, float, Callable], optional): when the cpu core should be created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the entity that must be terminated before the cpu core is created. Defaults to None.
            label (Optional[str], optional): the short description of the cpu core. Defaults to None.
        """
        super().__init__(at, after, label)
        self._ipc = ipc
        self._frequency = frequency
        self._cpu_id = cpu.id
        self._computational_power = Resource(
            capacity=ipc * frequency / simulation.cpu_acceleration,
            label=f"{self.__class__.__name__} {self.label} Capacity",
        )
        self._processes = list()
        simulation.CPU_CORES.append(self)

    def creation(self):
        """Creates the cpu core."""
        return super().creation()

    def termination(self):
        """Terminates the cpu core."""
        return super().termination()

    def _power_on(self):
        """Power on the cpu core."""
        super()._power_on()

    def _power_off(self):
        """Power off the cpu core"""
        super()._power_off()

    def execute_process(self, process: vProcess, length: int):
        """Executes a process for a given length.

        Args:
            process (vProcess): the process to be executed.
            length (int): the length of instructions to be executed.
        """
        self.processes.append(process)
        self.computational_power.distribute(process, length)
        execution_time = length / self.computational_power.capacity
        process.executing_cores.append(self)
        process.status.append(EXECUTING)
        LOGGER.debug(
            f"{simulation.now:0.2f}:\tvCPUCore {self.label} is executing {length} instructions for {process .__class__.__name__} {process.label}, {self.availablity} Capaccity left."
        )

        def _clear_executed_instructions():
            if not process.failed:
                self.computational_power.release(process, length)
                process._progress += length
                process._current_scheduled_length -= length
                self.processes.remove(process)
                process.executing_cores.remove(self)
                process.status.remove(EXECUTING)
                cpu_time = length / self.computational_power.capacity * 1000
                if process.__class__.__name__ != "vPacketHandler":
                    process.container.cpu.release(process, cpu_time) #type: ignore
                LOGGER.debug(
                    f"{simulation.now:0.2f}:\tvCPUCore {self.label} executed {length} instructions for {process .__class__.__name__} {process.label}, {self.availablity} Capacity left."
                )
                if process.__class__.__name__ != "vPacketHandler":
                    LOGGER.debug(
                        f"{simulation.now:0.2f}:\tvProcess {process.label} progress: {process.progress/process.length}, released {cpu_time} CPU Time of vContainer {process.container.label}, current CPU Time capacity {process.container.cpu.available_quantity}." #type: ignore
                    )
                else:
                    LOGGER.debug(
                        f"{simulation.now:0.2f}:\tvPacketHandler {process.label} progress: {process.progress/process.length}, released {cpu_time} CPU Time of vHost {process.host.label}, current CPU Time capacity {process.host.cpu.availablity}."
                    )

                Actor(
                    at=simulation.now,
                    action=process.complete,
                    label=f"vProcess {process.label} Clear Executed Instructions",
                    priority=PROCESS_COMPLETE_CHECK,
                )

                Actor(
                    at=simulation.now,
                    action=self.cpu.schedule_process,
                    label=f"vCPU {self.cpu.label} Schedule Processes",
                    priority=CPU_SCHEDULE_PROCESS,
                )

        Actor(
            at=simulation.now + execution_time,
            action=_clear_executed_instructions,
            label=f"vCPUCore {self.label} Clear Executed Instructions",
            priority=CORE_CLEAR_INSTRUCTIONS,
        )

    @property
    def ipc(self) -> Union[int, float]:
        """returns the instructions per cycle of the cpu core."""
        return self._ipc

    @property
    def frequency(self) -> Union[int, float]:
        """returns the frequency of the cpu core."""
        return self._frequency

    @property
    def computational_power(self) -> Resource:
        """returns the computational power ( as Resource ) of the cpu core."""
        return self._computational_power

    @property
    def capacity(self) -> Union[int, float]:
        """returns the capacity of the cpu core, aka how many instructions can be executed per second."""
        return self.computational_power.capacity

    @property
    def availablity(self) -> Union[int, float]:
        """returns the availablity of the cpu core in number of instructions."""
        return self.computational_power.available_quantity

    @property
    def utilization(self) -> Union[int, float]:
        """returns the utilization of the cpu core in percentage."""
        return self.computational_power.utilization * 100

    @property
    def processes(self) -> List[vProcess]:
        """returns the processes that are currently executing on the cpu core."""
        return self._processes

    @property
    def cpu(self) -> vCPU:
        """returns the cpu that this cpu core belongs to."""
        for cpu in simulation.CPUS:
            if cpu.id == self._cpu_id:
                return cpu
        raise RuntimeError(f"vCPUCore {self.label} can not found its associated vCPU.")
