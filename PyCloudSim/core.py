from __future__ import annotations
from ipaddress import IPv4Network
from typing import List, Union, TYPE_CHECKING
import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.layout import spring_layout
from networkx.drawing.nx_pylab import (
    draw_networkx_nodes,
    draw_networkx_edges,
    draw_networkx_labels,
)
from Akatosh import Mundus

if TYPE_CHECKING:
    from .status import *
    from .priority import *
    from .entity import *
    from .monitor import *
    from .scheduler import *

X86_64 = "x86-64"
ARM = "ARM"


class Simulation:
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(Simulation, cls).__new__(cls)
        return cls.instance

    def __init__(
        self,
        platform=X86_64,
        cpu_acceleration: int = 1000000,
        ram_amplifier: int = 100000,
        packet_size_amplifier: int = 1,
        virtual_network: str = "10.0.0.0/8",
        accuracy: int = 4,
    ):
        """The simulation object.

        Args:
            platform (_type_, optional): the host cpu architecture. Defaults to X86_64.
            cpu_acceleration (int, optional): this value is used to amplify the vProcess length, so 1 instruction becomes 1 x cpu_acceleration. Defaults to 1000000.
            ram_amplifier (int, optional): this value is used to amplify the vProcess RAM usage, so 1MB becomes 1 x ram_amplifier MB. Defaults to 100000.
            packet_size_amplifier (int, optional): this value is used to amplify the vPacket size, so 1MB becomes 1 x packet_size_amplifier MB. Defaults to 1.
            accuracy (int, optional): the accuracy of the simulation. Defaults to 4 means 0.00005 as the minimum time unit.
        """
        self._platform = platform
        self._cpu_acceleration = cpu_acceleration
        self._ram_amplifier = ram_amplifier
        self._packet_size_amplifier = packet_size_amplifier

        self._volumes: List[vVolume] = list()
        self._packets: List[vPacket] = list()
        self._processes: List[vProcess] = list()
        self._requests: List[vRequest] = list()
        self._containers: List[vContainer] = list()
        self._networkservices: List[vNetworkService] = list()
        self._microservices: List[vMicroservice] = list()
        self._sfcs: List[vSFC] = list()
        self._users: List[vUser] = list()
        self._nics: List[vNIC] = list()
        self._cpu_cores: List[vCPUCore] = list()
        self._cpus: List[vCPU] = list()
        self._routers: List[vRouter] = list()
        self._switches: List[vSwitch] = list()
        self._hosts: List[vHost] = list()
        self._workflows: List[WorkFlow] = list()
        self._user_requests: List[vUserRequest] = list()

        # place holder for schedulers
        self._container_scheduler: ContainerScheduler = None  # type: ignore
        self._request_scheduler: RequestScheduler = None  # type: ignore
        self._host_privisioner: HostProvisioner = None  # type: ignore
        self._volume_allocator: VolumeAllocator = None  # type: ignore

        # place holder for monitors
        self._user_request_monitor: UserRequestMonitor = None  # type: ignore
        self._workflow_monitor: WorkFlowMonitor = None  # type: ignore
        self._packet_monitor: PacketMonitor = None  # type: ignore
        self._request_monitor: RequestMonitor = None  # type: ignore

        # place holder for core network equipment
        self._gateway: vGateway = None  # type: ignore
        self._gateway_router: vRouter = None  # type: ignore
        self._core_switch: vSwitch = None  # type: ignore

        # initialize the topology
        self._topology = nx.DiGraph()

        # initialize the container network
        try:
            self._virtual_network = IPv4Network(virtual_network)
            self._virtual_network_ips = list(self._virtual_network.hosts())
        except:
            raise ValueError("Invalid container network.")

        # initialize the environment
        self._env = Mundus
        self._env.accuracy = accuracy

    def run(self, till: Union[int, float]):
        """Run the simulation.

        Args:
            till (Union[int, float]): time to run the simulation.
        """

        if self.container_scheduler is None:
            raise RuntimeError("Container scheduler is not defined.")

        if self.host_privisioner is None:
            raise RuntimeError("Host scheduler is not defined.")

        if self.volume_allocator is None:
            raise RuntimeError("Volume allocator is not defined.")

        if self.request_scheduler is None:
            raise RuntimeError("Request scheduler is not defined.")

        self._env.simulate(till=till)

        if self.packet_monitor is not None:
            self.packet_monitor.collect()
        if self.request_monitor is not None:
            self.request_monitor.collect()
        if self.workflow_monitor is not None:
            self.workflow_monitor.collect()
        if self.user_request_monitor is not None:
            self.user_request_monitor.collect()

    def draw(self, save: bool = False):
        """Draw the topology.

        Args:
            save (bool, optional): save the topology plot if true. Defaults to False.
        """
        fig, ax = plt.subplots()
        label_mapping = dict()
        for host in self.HOSTS:
            label_mapping[host] = host.label
        label_mapping[self.gateway] = self.gateway.label
        label_mapping[self.gateway_router] = self.gateway_router.label
        label_mapping[self.core_switch] = self.core_switch.label
        pos = spring_layout(self.topology)
        for host in self.HOSTS:
            draw_networkx_nodes(
                self.topology, pos, ax=ax, nodelist=[host], node_color="tab:green"
            )
        draw_networkx_nodes(
            self.topology, pos, ax=ax, nodelist=[self.gateway], node_color="tab:blue"
        )
        draw_networkx_nodes(
            self.topology,
            pos,
            ax=ax,
            nodelist=[self.core_switch],
            node_color="tab:blue",
        )
        draw_networkx_nodes(
            self.topology,
            pos,
            ax=ax,
            nodelist=[self.gateway_router],
            node_color="tab:blue",
        )
        for edge in self.topology.edges:
            draw_networkx_edges(
                self.topology, pos, ax=ax, edgelist=[edge], edge_color="tab:gray"
            )
        draw_networkx_labels(
            self.topology, pos, labels=label_mapping, ax=ax, font_size=6
        )
        plt.show()
        if save:
            fig.savefig(f"Topology.png")

    @property
    def platform(self):
        """Returns the platform of the simulation."""
        return self._platform

    @property
    def VOLUMES(self):
        """Returns the list of volumes."""
        return self._volumes

    @property
    def PACKETS(self):
        """Returns the list of packets."""
        return self._packets

    @property
    def PROCESSES(self):
        """Returns the list of processes."""
        return self._processes

    @property
    def REQUESTS(self):
        """Returns the list of requests."""
        return self._requests

    @property
    def CONTAINERS(self):
        """Returns the list of containers."""
        return self._containers

    @property
    def MICROSERVICES(self):
        """Returns the list of microservices."""
        return self._microservices

    @property
    def SFCS(self):
        """Returns the list of SFCS."""
        return self._sfcs

    @property
    def USERS(self):
        """Returns the list of users."""
        return self._users

    @property
    def NICS(self):
        """Returns the list of NICs."""
        return self._nics

    @property
    def CPU_CORES(self):
        """Returns the list of CPU cores."""
        return self._cpu_cores

    @property
    def CPUS(self):
        """Returns the list of CPUs."""
        return self._cpus

    @property
    def HOSTS(self):
        """Returns the list of hosts."""
        return self._hosts

    @property
    def env(self):
        """Returns the simulation environment."""
        return self._env

    @property
    def now(self):
        """Returns the current time of the simulation."""
        return self.env.now

    @property
    def cpu_acceleration(self):
        """Returns the CPU acceleration of the simulation."""
        return self._cpu_acceleration

    @property
    def ram_amplifier(self):
        """Returns the RAM amplifier of the simulation."""
        return self._ram_amplifier

    @property
    def container_scheduler(self):
        """Returns the container scheduler of the simulation."""
        return self._container_scheduler

    @property
    def request_scheduler(self):
        """Returns the request scheduler of the simulation."""
        return self._request_scheduler

    @property
    def host_privisioner(self):
        """Returns the host scheduler of the simulation."""
        return self._host_privisioner

    @property
    def topology(self):
        """Returns the topology of the simulation."""
        return self._topology

    @property
    def SWITCHES(self):
        """Returns the list of switches."""
        return self._switches

    @property
    def gateway(self):
        """Returns the gateway of the simulation."""
        return self._gateway

    @property
    def gateway_router(self):
        """Returns the gateway router of the simulation."""
        return self._gateway_router

    @property
    def core_switch(self):
        """Returns the core switch of the simulation."""
        return self._core_switch

    @property
    def volume_allocator(self):
        """Returns the volume allocator of the simulation."""
        return self._volume_allocator

    @property
    def NETWORKSERVICES(self):
        """Returns the list of network services."""
        return self._networkservices

    @property
    def packet_monitor(self):
        """Returns the packet monitor of the simulation."""
        return self._packet_monitor

    @property
    def packet_size_amplifier(self):
        """Returns the packet size amplifier of the simulation."""
        return self._packet_size_amplifier

    @property
    def ROUTERS(self):
        """Returns the list of routers."""
        return self._routers

    @property
    def virtual_network(self):
        """Returns the container network of the simulation."""
        return self._virtual_network

    @property
    def virtual_network_ips(self):
        """Returns the container network of the simulation."""
        return self._virtual_network_ips

    @property
    def request_monitor(self):
        """Returns the request monitor of the simulation."""
        return self._request_monitor

    @property
    def workflow_monitor(self):
        """Returns the workflow monitor of the simulation."""
        return self._workflow_monitor

    @property
    def WORKFLOWS(self):
        """Returns the workflow of the simulation."""
        return self._workflows

    @property
    def USER_REQUESTS(self):
        return self._user_requests

    @property
    def user_request_monitor(self):
        return self._user_request_monitor


simulation = Simulation()
