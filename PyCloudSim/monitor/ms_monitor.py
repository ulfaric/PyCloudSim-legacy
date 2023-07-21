from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

from Akatosh import Actor
import pandas as pd

from ..core import simulation
from ..priority import *

if TYPE_CHECKING:
    from ..entity import vMicroservice


class MSMonitor:
    _monitored_ms: Union[vMicroservice, List[vMicroservice]]
    _df: pd.DataFrame

    def __init__(
        self,
        monitored_host: Optional[vMicroservice | List[vMicroservice]] = None,
        monitor_interval: Union[int, float] = 0.01,
    ) -> None:
        """vMicroservice Monitor.

        Args:
            monitored_host (Optional[vMicroservice  |  List[vMicroservice]], optional): if one, all microservices will be monitored. Defaults to None.
            monitor_interval (Union[int, float], optional): the sampling interval. Defaults to 0.01.
        """        
        if monitored_host is None:
            self._monitored_ms = simulation.MICROSERVICES
        else:
            self._monitored_ms = monitored_host
        self._monitor_interval = monitor_interval

        self._df = pd.DataFrame(
            {
                "ms": pd.Series(dtype="str"),
                "ms_id": pd.Series(dtype="str"),
                "time": pd.Series(dtype="float"),
                "cpu_util": pd.Series(dtype="float"),
                "ram_util": pd.Series(dtype="float"),
                "num_containers": pd.Series(dtype="int"),
                "num_scheduled_containers": pd.Series(dtype="int"),
                "num_non_scheduled_containers": pd.Series(dtype="int"),
            }
        )
            
        self._process = Actor(
            at=0,
            step=self.monitor_interval,
            action=self.action,
            priority=MONITOR_PRIORITY,
            label="Host Monitor",
        )

    def action(self):
        """Telemetries collection."""
        if isinstance(self._monitored_ms, list):
            for ms in self._monitored_ms:
                if not ms.terminated:
                    host_telemetry = pd.DataFrame(
                        {
                            "ms": ms.label,
                            "ms_id": str(ms.id),
                            "time": float(simulation.now),
                            "cpu_util": ms.cpu_usage_in_past(self.monitor_interval),
                            "ram_util": ms.ram_usage_in_past(self.monitor_interval),
                            "num_containers": len(ms.containers),
                            "num_scheduled_containers": len(
                                [
                                    container
                                    for container in ms.containers
                                    if container.scheduled
                                ]
                            ),
                            "num_non_scheduled_containers": len(
                                [
                                    container
                                    for container in ms.containers
                                    if not container.scheduled
                                ]
                            ),
                        },
                        index=[0],
                    )
                    self._df = pd.concat([self._df, host_telemetry], ignore_index=True)
        elif isinstance(self.monitored_ms, vMicroservice):
            host_telemetry = pd.DataFrame(
                {
                    "ms": self.monitored_ms.label,
                    "ms_id": str(self.monitored_ms.id),
                    "time": float(simulation.now),
                    "cpu_util": self.monitored_ms.cpu_usage_in_past(self.monitor_interval),
                    "ram_util": self.monitored_ms.cpu_usage_in_past(self.monitor_interval),
                    "num_containers": len(self.monitored_ms.containers),
                    "num_scheduled_containers": len(
                        [
                            container
                            for container in self.monitored_ms.containers
                            if container.scheduled
                        ]
                    ),
                    "num_non_scheduled_containers": len(
                        [
                            container
                            for container in self.monitored_ms.containers
                            if not container.scheduled
                        ]
                    ),
                },
                index=[0],
            )
            self._df = pd.concat([self._df, host_telemetry], ignore_index=True)

    @property
    def df(self):
        """The pandas dataframe of the host monitor."""
        return self._df

    @property
    def monitored_ms(self) -> Union[vMicroservice, List[vMicroservice]]:
        """The monitored microservices."""
        return self._monitored_ms

    @property
    def monitor_interval(self) -> Union[int, float]:
        """The sampling interval."""
        return self._monitor_interval