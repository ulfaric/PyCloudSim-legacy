from __future__ import annotations
from math import inf

from typing import TYPE_CHECKING, List, Optional, Union

from Akatosh import Actor
import pandas as pd

from ..core import simulation
from ..priority import *
from ..entity import vHost

if TYPE_CHECKING:
    from ..entity import PhysicalEntity


class HostMonitor:
    _monitored_hosts: Union[PhysicalEntity, List[PhysicalEntity]]
    _df: pd.DataFrame

    def __init__(
        self,
        monitored_host: Optional[PhysicalEntity | List[PhysicalEntity]] = None,
        monitor_interval: Union[int, float] = 0.01,
    ) -> None:
        """Host monitor.

        Args:
            monitored_host (Optional[PhysicalEntity  |  List[PhysicalEntity]], optional): if none, all simulated physical entity will be monitored. Defaults to None.
            monitor_interval (Union[int, float], optional): the sampling interval. Defaults to 0.01.
        """        
        if monitored_host is None:
            self._monitored_hosts = []
            self._monitored_hosts.extend(simulation.HOSTS)
            self._monitored_hosts.extend(simulation.SWITCHES)
            self._monitored_hosts.extend(simulation.ROUTERS)
        else:
            self._monitored_hosts = monitored_host
        self._monitor_interval = monitor_interval

        self._df = pd.DataFrame(
            {
                "host_id": pd.Series(dtype="str"),
                "host_label": pd.Series(dtype="str"),
                "time": pd.Series(dtype="float"),
                "cpu_util": pd.Series(dtype="float"),
                "ram_util": pd.Series(dtype="float"),
                "rom_util": pd.Series(dtype="float"),
                "bw_in_util": pd.Series(dtype="float"),
                "bw_out_util": pd.Series(dtype="float"),
                "num_containers": pd.Series(dtype="int"),
                "num_processes": pd.Series(dtype="int"),
                "power_usage": pd.Series(dtype="float"),
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
        """Telemetries collection.
        """
        if isinstance(self._monitored_hosts, list):
            for host in self._monitored_hosts:
                if host.created:
                    host_telemetry = pd.DataFrame(
                        {
                            "host_id": str(host.id),
                            "host_label": host.label,
                            "time": float(simulation.now),
                            "cpu_util": host.cpu.utilization_in_past(
                                self.monitor_interval
                            ),
                            "ram_util": host.ram.utilization_in_past(
                                self.monitor_interval
                            ),
                            "rom_util": host.rom.utilization_in_past(
                                self.monitor_interval
                            ),
                            "bw_in_util": host.uplink_utilization(
                                self.monitor_interval
                            ),
                            "bw_out_util": host.downlink_utilization(
                                self.monitor_interval
                            ),
                            "num_containers": len(host.containers)
                            if type(host) == vHost
                            else 0,
                            "num_processes": len(host.processes),
                            "power_usage": host.power_usage(self.monitor_interval),
                        },
                        index=[0],
                    )
                    self._df = pd.concat([self._df, host_telemetry], ignore_index=True)
        elif isinstance(self.monitored_hosts, vHost):
            if self.monitored_hosts.created:
                host_telemetry = pd.DataFrame(
                    {
                        "host_id": str(self.monitored_hosts.id),
                        "host_label": self.monitored_hosts.label,
                        "time": float(simulation.now),
                        "cpu_util": self.monitored_hosts.cpu.utilization_in_past(
                            self.monitor_interval
                        ),
                        "ram_util": self.monitored_hosts.ram.utilization_in_past(
                            self.monitor_interval
                        ),
                        "rom_util": self.monitored_hosts.rom.utilization_in_past(
                            self.monitor_interval
                        ),
                        "bw_in_util": self.monitored_hosts.uplink_utilization(
                            self.monitor_interval
                        ),
                        "bw_out_util": self.monitored_hosts.downlink_utilization(
                            self.monitor_interval
                        ),
                        "num_containers": len(self.monitored_hosts.containers)
                        if type(self.monitored_hosts) == vHost
                        else 0,
                        "num_processes": len(self.monitored_hosts.processes),
                        "power_usage": self.monitored_hosts.power_usage(
                            self.monitor_interval
                        ),
                    },
                    index=[0],
                )
                self._df = pd.concat([self._df, host_telemetry], ignore_index=True)

    @property
    def df(self):
        """The pandas dataframe containing the telemetry data."""
        return self._df

    @property
    def monitored_hosts(self):
        """The monitored hosts."""
        return self._monitored_hosts

    @property
    def monitor_interval(self) -> Union[int, float]:
        """The sampling interval."""
        return self._monitor_interval
