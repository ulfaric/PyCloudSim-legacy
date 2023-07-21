from .core import simulation
from .entity import vGateway, vRouter, vSwitch
from .scheduler import *


def default_settings(
    host_evaluation_period: Union[int, float] = 1,
):
    """Set default settings for PyCloudSim.

    Args:
        host_evaluation_period (Union[int, float], optional): host evaluation  period. Defaults to 1.
    """
    host_privisioner = HostProvisioner(evaluation_interval=host_evaluation_period)
    container_scheduler = ContainerSchedulerBestfit()
    volumn_allocator = VolumeAllocator()
    request_scheduler = RequestScheduler()


def initiate_topology(gateway_bandwidth: int = 100000):
    simulation._gateway = vGateway(label="Gateway")
    simulation._gateway_router = vRouter(
        ipc=1, frequency=5000, num_cpu_cores=4, ram=16, label="Gateway Router"
    )
    simulation.gateway_router.connect_device(
        simulation.gateway, bandwidth=gateway_bandwidth
    )
    simulation._core_switch = vSwitch(
        ipc=1,
        frequency=5000,
        num_cpu_cores=4,
        ram=16,
        subnet="192.168.0.0/24",
        label="Core Switch",
    )
    simulation.gateway_router.connect_device(simulation.core_switch)
