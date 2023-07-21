from __future__ import annotations
from abc import ABC
import re
from typing import TYPE_CHECKING, Union

from Akatosh import Actor

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from ..requests import *
from ..entity import vMicroservice

if TYPE_CHECKING:
    from ..entity import vContainer, vRequest, vProcess


class RequestScheduler:
    def __init__(self) -> None:
        """Request Scheduler
        """        
        self._active_process: Actor = None  # type: ignore
        simulation._request_scheduler = self

    def schedule(self):
        """Schedule requests.
        """        
        def _schedule():
            LOGGER.debug(
                f"{simulation.now:0.2f}:\tRequest Scheduler is scheduling...{len([req for req in simulation.REQUESTS if req.scheduled == False])} requests."
            )
            self._active_process = None  # type: ignore
            simulation.REQUESTS.sort(key=lambda x: x.priority)
            for request in simulation.REQUESTS:
                source_endpoint = None
                target_endpoint = None
                if not request.scheduled and request.created:
                    # find the containers
                    if isinstance(request.source, vMicroservice):
                        source_endpoint = request.source.service.loadbalancer()
                    else:
                        source_endpoint = None

                    if isinstance(request.target, vMicroservice):
                        target_endpoint = request.target.service.loadbalancer()
                    else:
                        target_endpoint = None

                    # check if request schedulable
                    if (
                        source_endpoint is None
                        and isinstance(request.source, vMicroservice)
                    ) or (
                        target_endpoint is None
                        and isinstance(request.target, vMicroservice)
                    ):
                        LOGGER.debug(f"{simulation.now:0.2f}:\tvRequest {request.label} not schedulable, {request.source} or {request.target} not available.")
                        continue

                    request._scheduled_at = simulation.now
                    request.status.append(SCHEDULED)
                    if request.flow is not None and not request.flow.scheduled:
                        request.flow._scheduled_at = simulation.now
                        request.flow.status.append(SCHEDULED)

                    if source_endpoint is not None:
                        request._source_endpoint = source_endpoint
                        source_endpoint.accept_request(request)

                    if target_endpoint is not None:
                        request._target_endpoint = target_endpoint
                        target_endpoint.accept_request(request)

                    request.execute()

        if self._active_process is None:
            self._active_process = Actor(
                at=simulation.now,
                action=_schedule,
                label=f"vRequest Scedule Start",
                priority=REQUEST_SCHEDULER,
            )

    @property
    def active_process(self) -> Actor:
        """return the active process of the request scheduler."""
        return self._active_process
