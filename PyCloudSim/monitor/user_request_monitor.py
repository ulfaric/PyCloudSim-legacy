from __future__ import annotations

import pandas as pd

from ..core import simulation
from ..priority import *




class UserRequestMonitor:
    _df: pd.DataFrame

    def __init__(
        self,
    ) -> None:
        self._df = pd.DataFrame(
            {
                "user_request_id": pd.Series(dtype="str"),
                "user_request_label": pd.Series(dtype="str"),
                "sfc_id": pd.Series(dtype="str"),
                "created_at": pd.Series(dtype="float"),
                "scheduled_at": pd.Series(dtype="float"),
                "terminated_at": pd.Series(dtype="float"),
                "successful": pd.Series(dtype="bool"),
            }
        )
        simulation._user_request_monitor = self

    def collect(self):
        for user_request in simulation.USER_REQUESTS:
            user_request_telemetry = pd.DataFrame(
                {
                    "user_request_id": str(user_request.id),
                    "user_request_label": user_request.label,
                    "sfc_id": str(user_request.sfc.id),
                    "created_at": float(user_request.created_at),
                    "scheduled_at": float(user_request.scheduled_at),
                    "terminated_at": float(user_request.terminated_at),
                    "successful": user_request.completed,
                },
                index=[0],
            )
            self._df = pd.concat(
                [self._df, user_request_telemetry], ignore_index=True
            )

    @property
    def df(self):
        return self._df
