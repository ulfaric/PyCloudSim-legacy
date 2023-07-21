from __future__ import annotations
from math import inf
from typing import List, Optional, TYPE_CHECKING, Union, Callable, Tuple
import matplotlib.pyplot as plt

from ..core import simulation
from ..logger import LOGGER
from ..status import *
from ..requests import *
from ..priority import *
from .v_entity import Entity
from .v_virtual_entity import VirtualEntity

if TYPE_CHECKING:
    from .v_microservice import vMicroservice
    from .v_networkservice import vNetworkService


class vSFC(VirtualEntity):
    def __init__(
        self,
        entry: Optional[Tuple[vMicroservice, str]] = None,
        exit: Optional[Tuple[vMicroservice, str]] = None,
        path: Optional[List[Tuple[vMicroservice, vMicroservice, str]]] = None,
        network_service: Optional[vNetworkService] = None,
        internal: bool = False,
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vSFC (with respective of a network service)

        Args:
            entry (Optional[vMicroservice], optional): the entry point of the SFC, aka the microservice that will accept user's request at the beginning. Defaults to None, must be set if the sfc is not internal.
            exit (Optional[vMicroservice], optional): the exit point of the SFC, aka the microservice that will return user's request at the last. Defaults to None.
            path (Optional[List[Tuple[vMicroservice, vMicroservice]]], optional): the path of the engaged microservices, must be a list of tuple of two microservice. Defaults to None.
            network_service (Optional[vNetworkService], optional): the associated network service. Defaults to None.
            process_length (Union[int, Callable], optional): the process length of each request. Defaults to 100, can alse be a callable function.
            packet_size (Union[int, Callable], optional): the packet size of each packet. Defaults to 65536, can alse be a callable function.
            num_packets (Union[int, Callable], optional): the number of packets per request. Defaults to 1, can alse be a callable function.
            priority (int, optional): the priority of the SFC. Defaults to 0.
            num_users (int, optional): the number of users. Defaults to 1.
            internal (bool, optional): set true for internal SFC, aka the engaged microservices does not need to communicate with the user. Defaults to False.
            retry (bool, optional): if true, failed user will have its request being re-initialized. Defaults to False.
            at (Union[int, float, Callable], optional): when the SFC will be created. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): the other SFCs that must complete before this SFC. Defaults to None.
            label (Optional[str], optional): short description of this SFC. Defaults to None.
        """
        super().__init__(at, after, label)
        # check if the vSFC is valid
        self._entry = entry
        self._exit = exit
        self._path = path if path is not None else list()

        if path is not None:
            if self.entry is not None:
                if self.entry[0] is not path[0][0]:
                    raise ValueError(
                        f"Start vMicroservice {self.entry[0].label} is not the same as the first node {path[0][0].label} in the path"
                    )
            if self.exit is not None:
                if self.exit[0] is not path[-1][1]:
                    raise ValueError(
                        f"End vMicroservice {self.exit[0].label} is not the same as the last node {path[-1][1].label} in the path"
                    )

        # check if the vSFC is valid with respect to the vNetworkService
        self._ns_id = network_service.id if network_service is not None else None
        if self.network_service is not None:
            if self.entry is not None:
                if isinstance(self.network_service.entry, list):
                    if self.entry[0] not in self.network_service.entry:
                        raise ValueError(
                            f"vSFC {self.label} Start vMicroservice {self.entry[0].label} is not one of the entries vNetworkService {self.network_service.label}"
                        )
                else:
                    if self.entry[0] is not self.network_service.entry:
                        raise ValueError(
                            f"vSFC {self.label} Start vMicroservice {self.entry[0].label} is not the entry vNetworkService {self.network_service.label}"
                        )
            if self.exit is not None:
                if isinstance(self.network_service.exit, list):
                    if self.exit[0] not in self.network_service.exit:
                        raise ValueError(
                            f"vSFC {self.label} End vMicroservice {self.exit[0].label} is not one of the exits vNetworkService {self.network_service.label}"
                        )
                else:
                    if self.exit[0] is not self.network_service.exit:
                        raise ValueError(
                            f"vSFC {self.label} End vMicroservice {self.exit[0].label} is not the exit vNetworkService {self.network_service.label}"
                        )

        self._microservices: List[vMicroservice] = list()
        for link in self.path:
            if link[0] not in self.microservices:
                self.microservices.append(link[0])
            if link[1] not in self.microservices:
                self.microservices.append(link[1])
        self._users = list()
        self._internal = internal
        self._after: Union[vSFC, List[vSFC]] = after  # type: ignore
        simulation.SFCS.append(self)

    def termination(self):
        """Terminate the vSFC and all its microservices."""
        super().termination()
        for ms in self.microservices:
            if not ms.terminated:
                ms.terminate()

    def evaluate(self):
        """Evaluate the vSFC and all its microservices. Change the status of the vSFC to READY if all its microservices are ready."""
        if all(ms.ready for ms in self.microservices):
            self.status.append(READY)
            LOGGER.info(f"{simulation.now:0.2f}:\tvSFC {self.label} is ready.")
        else:
            if self.ready:
                self.status.remove(READY)

    @property
    def entry(self):
        """The entry point of the SFC, aka the microservice that will accept user's request at the beginning."""
        return self._entry

    @property
    def exit(self):
        """The exit point of the SFC, aka the microservice that will return user's request at the last."""
        return self._exit

    @property
    def path(self):
        """The path of the engaged microservices, must be a list of tuple of two microservice and request type."""
        return self._path

    @property
    def users(self):
        """The users of the vSFC."""
        return self._users

    @property
    def microservices(self):
        """The microservices of the vSFC."""
        return self._microservices

    @property
    def network_service(self) -> Optional[vNetworkService]:
        """The associated network service."""
        if self._ns_id is not None:
            for ns in simulation.NETWORKSERVICES:
                if ns.id == self._ns_id:
                    return ns
            raise RuntimeError(
                f"vSFC {self.label} cannot find its associated network service"
            )
        else:
            return None

    @property
    def internal(self):
        """Return true if the vSFC is internal, aka the engaged microservices does not need to communicate with the user."""""
        return self._internal

    @property
    def after(self):
        """Same as entity."""
        return self._after

    @property
    def ready(self):
        """Return true if the vSFC is ready, aka all its microservices are ready."""
        return READY in self.status
