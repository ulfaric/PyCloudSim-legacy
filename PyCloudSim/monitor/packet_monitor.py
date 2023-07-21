from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

import pandas as pd

from ..core import simulation
from ..priority import *

if TYPE_CHECKING:
    from ..entity import vPacket


class PacketMonitor:
    _df: pd.DataFrame

    def __init__(
        self,
    ) -> None:
        self._df = pd.DataFrame(
            {
                "packet_id": pd.Series(dtype="str"),
                "packet_label": pd.Series(dtype="str"),
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

        simulation._packet_monitor = self

    def collect(self):
        for packet in simulation.PACKETS:
            new_user_telemetry = pd.DataFrame(
                {
                    "packet_id": str(packet.id),
                    "packet_label": packet.label,
                    "request_id": str(packet.request.id)
                    if packet.request is not None
                    else None,
                    "request_label": packet.request.label
                    if packet.request is not None
                    else None,
                    "user_id": str(packet.request.user.id)
                    if packet.request is not None and packet.request.user is not None
                    else None,
                    "user_label": packet.request.user.label
                    if packet.request is not None and packet.request.user is not None
                    else None,
                    "created_at": float(packet.created_at),
                    "scheduled_at": float(packet.scheduled_at),
                    "terminated_at": float(packet.terminated_at),
                    "successful": packet.completed,
                },
                index=[0],
            )
            self._df = pd.concat([self._df, new_user_telemetry], ignore_index=True)

    @property
    def df(self) -> pd.DataFrame:
        return self._df
