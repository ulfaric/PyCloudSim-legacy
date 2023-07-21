from __future__ import annotations
import random
from subprocess import call
from typing import List, Optional, TYPE_CHECKING, Union, Callable, Any

from Akatosh import Actor

from PyCloudSim.core import simulation
from PyCloudSim.entity.v_entity import Entity

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..priority import *
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity
from .v_request import vRequest

if TYPE_CHECKING:
    from .v_sfc import vSFC


class WorkFlow(VirtualEntity):
    def __init__(
        self,
        user: vUser,
        user_request: vUserRequest,
        sfc: vSFC,
        process_length: Union[int, Callable] = 100,
        packet_size: Union[int, Callable] = 65536,
        num_packets: Union[int, Callable] = 1,
        priority: Union[int, Callable] = 0,
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        """Create a new WorkFlow.

        Args:
            user (vUser): the vUser.
            sfc (vSFC): the vSFC.
            process_length (Union[int, Callable], optional): the process length. Defaults to 100.
            packet_size (Union[int, Callable], optional): the packet size. Defaults to 65536.
            num_packets (Union[int, Callable], optional): the number of packet (Do not change the GET/ACK packet). Defaults to 1.
            priority (Union[int, Callable], optional): the priority of the workflow. Defaults to 0.
            retry (Union[bool, Callable], optional): set true for retrying until complete. Defaults to True.
            retry_delay (_type_, optional): the delay beofore retrying the workflow. Defaults to lambda:random.random().
            at (int | float | Callable[..., Any], optional): when the workflow should be created. Defaults to simulation.now.
            after (Entity | List[Entity] | None, optional): the entity that the workflow must be created after. Defaults to None.
            label (str | None, optional): short desciption of the workflow. Defaults to None.
        """
        super().__init__(at, after, label)
        self._user = user
        self._user_request = user_request
        self._sfc_id = sfc.id
        self._process_length = process_length
        self._packet_size = packet_size
        self._num_packets = num_packets
        self._priority = priority
        self._requests = list()
        self._on_creation = self.initialize_requests
        simulation.WORKFLOWS.append(self)

    def termination(self):
        if self.completed:
            self.user_request.complete()
        
        if self.failed:
            self.user_request.fail()            
        super().termination()

    def initialize_requests(self, delay: int | float = 0):
        if self.sfc.entry is not None and not self.sfc.internal:
            self.requests.append(
                vRequest(
                    at=simulation.now,
                    source=self.user,
                    target=self.sfc.entry[0],
                    flow=self,
                    type=self.sfc.entry[1],
                    label=f"{self.label}-R-{len(self.requests)}",
                )
            )
        # initialize path request
        for link in self.sfc.path:
            self.requests.append(
                vRequest(
                    at=simulation.now,
                    source=link[0],
                    target=link[1],
                    type=link[2],
                    flow=self,
                    label=f"{self.label}-R-{len(self.requests)}",
                    after=self.requests[-1] if len(self.requests) > 0 else None,
                )
            )
        # initialize tail request
        if self.sfc.exit is not None and not self.sfc.internal:
            self.requests.append(
                vRequest(
                    at=simulation.now,
                    source=self.sfc.exit[0],
                    target=self.user,
                    type=self.sfc.exit[1],
                    flow=self,
                    label=f"{self.label}-R-{len(self.requests)}",
                    after=self.requests[-1] if len(self.requests) > 0 else None,
                )
            )

        self.requests[-1]._on_termination = (
            lambda: self.complete()
            if self.requests[-1].completed and not self.failed
            else None
        )
        LOGGER.info(
            f"{simulation.now:0.2f}:\tWorkflow {self.label} initialized vRequests."
        )

    def complete(self):
        """COMPLETE the workflow and engage the termination process."""
        self.status.append(COMPLETED)
        self.terminate()
        LOGGER.info(f"{simulation.now:0.2f}:\tWorkflow {self.label} completed.")

    def fail(self):
        """Fail the workflow and engage the termination process if no retry is set."""
        self.status.append(FAILED)
        self.terminate()
        LOGGER.info(f"{simulation.now:0.2f}:\tWorkflow {self.label} failed.")

    @property
    def requests(self) -> List[vRequest]:
        return self._requests

    @property
    def user(self):
        return self._user

    @property
    def user_request(self):
        return self._user_request

    @property
    def process_length(self):
        return self._process_length

    @property
    def packet_size(self):
        return self._packet_size

    @property
    def num_packets(self):
        return self._num_packets

    @property
    def priority(self):
        return self._priority

    @property
    def sfc_id(self):
        return self._sfc_id

    @property
    def sfc(self) -> vSFC:
        for sfc in simulation.SFCS:
            if sfc.id == self._sfc_id:
                return sfc
        raise ValueError(f"SFCFlow {self.label} can not find its associated vSFC.")


class vUserRequest(VirtualEntity):
    def __init__(
        self,
        user: vUser,
        sfc: vSFC,
        priority: Union[int, Callable] = 0,
        retry: Union[bool, Callable] = True,
        backoff: Union[int, float, Callable] = lambda: random.random(),
        process_length: Union[int, Callable] = 100,
        packet_size: Union[int, Callable] = 65536,
        num_packets: Union[int, Callable] = 1,
        at: int | float | Callable[..., Any] = simulation.now,
        after: Entity | List[Entity] | None = None,
        label: str | None = None,
    ):
        """Create a new vUserRequest.

        Args:
            user (vUser): the vUser.
            sfc (vSFC): the requested vSFC.
            priority (Union[int, Callable], optional): the priority of the user request. Defaults to 0.
            retry (Union[bool, Callable], optional): set to true if repeat untill sucess. Defaults to True.
            backoff (_type_, optional): the random backoff. Defaults to lambda:random.random().
            process_length (Union[int, Callable], optional): the length of the generated process. Defaults to 100.
            packet_size (Union[int, Callable], optional): the size of the generated packets. Defaults to 65536.
            num_packets (Union[int, Callable], optional): the number of generated packets. Defaults to 1.
            at (int | float | Callable[..., Any], optional): same as entity. Defaults to simulation.now.
            after (Entity | List[Entity] | None, optional): same as entity. Defaults to None.
            label (str | None, optional): same as entity. Defaults to None.
        """
        super().__init__(at, after, label)
        self._user = user
        self._sfc_id = sfc.id
        self._priority = priority
        self._retry = retry
        self._backoff = backoff
        self._process_length = process_length
        self._packet_size = packet_size
        self._num_packets = num_packets
        self._flows: List[WorkFlow] = list()

    def creation(self):
        """Creation process of the vUserRequest"""
        self.initialize_workflow()
        simulation.USER_REQUESTS.append(self)
        return super().creation()

    def initialize_workflow(self, delay: int | float = 0):
        """Initialize a workflow for the user request."""
        def _initialize_workflow():
            if self.sfc.ready:
                flow = WorkFlow(
                    at=simulation.now,
                    user=self.user,
                    user_request=self,
                    sfc=self.sfc,
                    priority=self.priority,
                    process_length=self.process_length,
                    packet_size=self.packet_size,
                    num_packets=self.num_packets,
                    label=f"{self.label}-F-{len(self.flows)}",
                )
                self.flows.append(flow)
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvUser {self.label} requests SFC {self.sfc.label} as WorkFlow {flow.label}."
                )
            else:
                if callable(self.backoff):
                    Actor(
                        at=simulation.now + self.backoff(),
                        action=_initialize_workflow,
                        label=f"vUserRequest {self.label} Initialize Workflow",
                    )
                else:
                    Actor(
                        at=simulation.now + self.backoff,
                        action=_initialize_workflow,
                        label=f"vUserRequest {self.label} Initialize Workflow",
                    )
                LOGGER.info(
                    f"{simulation.now:0.2f}:\tvUserRequest {self.label} backs off Workflow initialization because SFC {self.sfc.label} is not ready."
                )
        Actor(
            at=simulation.now+delay,
            action=_initialize_workflow,
            label=f"vUserRequest {self.label} Initialize Workflow",
            priority=CREATION
        )

    def termination(self):
        """Termination process of the vUserRequest"""
        super().termination()
        if all(user_request.completed for user_request in simulation.USER_REQUESTS):
            simulation._env.stop()
        
    def fail(self):
        """Fail the user request and engage the termination process if no retry is set."""
        LOGGER.info(f"{simulation.now:0.2f}:\tvUserRequest {self.label} failed, retries.")
        if callable(self.backoff):
            self.initialize_workflow(delay=self.backoff())
        else:
            self.initialize_workflow(delay=self.backoff)
        
    def complete(self):
        """Complete the user request and engage the termination process."""
        self.status.append(COMPLETED)
        LOGGER.info(f"{simulation.now:0.2f}:\tvUserRequest {self.label} completed.")
        self.terminate()


    @property
    def user(self):
        """Return the vUser of the vUserRequest."""
        return self._user

    @property
    def process_length(self):
        """Return the process length of the vUserRequest."""
        return self._process_length

    @property
    def packet_size(self):
        """Return the packet size"""
        return self._packet_size

    @property
    def num_packets(self):
        """Return the number of packets"""
        return self._num_packets

    @property
    def priority(self):
        """Return the priority of the vUserRequest."""
        return self._priority

    @property
    def retry(self):
        """Return the retry of the vUserRequest."""
        return self._retry

    @property
    def backoff(self):
        """Return the backoff of the vUserRequest."""
        return self._backoff

    @property
    def sfc_id(self):
        """Return the sfc id of the vUserRequest."""
        return self._sfc_id

    @property
    def sfc(self) -> vSFC:
        """Return the vSFC of the vUserRequest."""
        for sfc in simulation.SFCS:
            if sfc.id == self._sfc_id:
                return sfc
        raise ValueError(f"SFCFlow {self.label} can not find its associated vSFC.")

    @property
    def flows(self) -> List[WorkFlow]:
        """Return the list of WorkFlows of the vUserRequest."""
        return self._flows


class vUser(VirtualEntity):
    _requests: List[vRequest]

    def __init__(
        self,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vUser."""
        super().__init__(at, after, label)

        self._user_requests: List[vUserRequest] = list()
        simulation.USERS.append(self)

    def creation(self):
        """Creation process of the vUser"""
        return super().creation()

    def termination(self):
        """Termination process of the vUser"""
        return super().termination()

    def request_sfc(
        self,
        sfc: vSFC,
        priority: Union[int, Callable] = 0,
        retry: Union[bool, Callable] = True,
        backoff: Union[int, float, Callable] = lambda: random.random(),
        process_length: Union[int, Callable] = 100,
        packet_size: Union[int, Callable] = 65536,
        num_packets: Union[int, Callable] = 1,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
    ):
        """Request a vSFC.

        Args:
            sfc (vSFC): the requested vSFC.
            priority (Union[int, Callable], optional): the priority of the user request. Defaults to 0.
            retry (Union[bool, Callable], optional): set to true if the user request will repeat untill sucess. Defaults to True.
            backoff (_type_, optional): the random backoff. Defaults to lambda:random.random().
            process_length (Union[int, Callable], optional): the length of generated process. Defaults to 100.
            packet_size (Union[int, Callable], optional): the packet size of the packet size. Defaults to 65536.
            num_packets (Union[int, Callable], optional): the number of the packet for this user request. Defaults to 1.
            at (Union[int, float, Callable], optional): same as entity. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): same as entity. Defaults to None.
        """        
        user_request = vUserRequest(
            at=at,
            after=after,
            user=self,
            sfc=sfc,
            priority=priority,
            process_length=process_length,
            packet_size=packet_size,
            num_packets=num_packets,
            retry=retry,
            backoff=backoff,
            label=f"U-{self.label}-R-{len(self.user_request)}-SFC-{sfc.label}",
        )
        self.user_request.append(user_request)
        return user_request

    @property
    def user_request(self) -> List[vUserRequest]:
        """The list of user requests of the vUser."""
        return self._user_requests
