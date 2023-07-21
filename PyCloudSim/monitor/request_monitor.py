from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

import pandas as pd

from ..core import simulation
from ..priority import *

if TYPE_CHECKING:
    from ..entity import vRequest


class RequestMonitor:
    """Request Monitor."""
    _df: pd.DataFrame

    def __init__(
        self,
    ) -> None:
        self._df = pd.DataFrame(
            {
                "request_id": pd.Series(dtype="str"),
                "request_label": pd.Series(dtype="str"),
                "user_id": pd.Series(dtype="str"),
                "user_label": pd.Series(dtype="str"),
                "created_at": pd.Series(dtype="float"),
                "scheduled_at": pd.Series(dtype="float"),
                "terminated_at": pd.Series(dtype="float"),
                "successful": pd.Series(dtype="bool"),
            }
        )

        simulation._request_monitor = self

    def collect(self):
        for request in simulation.REQUESTS:
            request_info = pd.DataFrame(
                {
                    "request_id": request.id,
                    "request_label": request.label,
                    "user_id": request.user.id if request.user else None,
                    "user_label": request.user.label if request.user else None,
                    "created_at": request.created_at,
                    "scheduled_at": request.scheduled_at,
                    "terminated_at": request.terminated_at,
                    "successful": request.completed,
                },
                index=[0],
            )
            self._df = pd.concat([self._df, request_info], ignore_index=True)

    @property
    def df(self) -> pd.DataFrame:
        return self._df
