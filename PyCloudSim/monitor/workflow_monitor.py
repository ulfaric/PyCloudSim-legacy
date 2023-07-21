from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

import pandas as pd

from ..core import simulation
from ..priority import *

if TYPE_CHECKING:
    from ..entity import vUser


class WorkFlowMonitor:
    _df: pd.DataFrame

    def __init__(
        self,
    ) -> None:
        self._df = pd.DataFrame(
            {
                "flow_id": pd.Series(dtype="str"),
                "flow_label": pd.Series(dtype="str"),
                "sfc_id": pd.Series(dtype="str"),
                "created_at": pd.Series(dtype="float"),
                "scheduled_at": pd.Series(dtype="float"),
                "terminated_at": pd.Series(dtype="float"),
                "successful": pd.Series(dtype="bool"),
            }
        )
        simulation._workflow_monitor = self

    def collect(self):
        for flow in simulation.WORKFLOWS:
            workflow_telemetry = pd.DataFrame(
                {
                    "flow_id": str(flow.id),
                    "flow_label": flow.label,
                    "sfc_id": str(flow.sfc.id),
                    "created_at": float(flow.created_at),
                    "scheduled_at": float(flow.scheduled_at),
                    "terminated_at": float(flow.terminated_at),
                    "successful": flow.completed,
                },
                index=[0],
            )
            self._df = pd.concat(
                [self._df, workflow_telemetry], ignore_index=True
            )

    @property
    def df(self):
        return self._df
