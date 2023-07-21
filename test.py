from PyCloudSim.entity import vMicroserviceDeafult, vHost, vNetworkService, vSFC, vUser
from PyCloudSim.monitor import (
    HostMonitor,
    PacketMonitor,
    MSMonitor,
    WorkFlowMonitor,
    RequestMonitor,
)
from PyCloudSim.core import simulation
from PyCloudSim.util import *
import random
from Akatosh import event

default_settings()
initiate_topology()
for i in range(2):
    vHost(num_cpu_cores=2, ipc=1, frequency=2000, ram=16, rom=32, label=f"Host {i}")

ms1 = vMicroserviceDeafult(
    cpu=40,
    cpu_limit=80,
    ram=512,
    ram_limit=1024,
    image_size=100,
    volumes=[("test", "test", 100, False), ("test2", "test", 100, True)],
    min_num_containers=4,
    max_num_containers=5,
    label="Microservice 1",
    deamon=False,
)

ms2 = vMicroserviceDeafult(
    cpu=40,
    cpu_limit=80,
    ram=512,
    ram_limit=1024,
    image_size=100,
    volumes=[("test", "test", 100, False), ("test2", "test", 100, True)],
    min_num_containers=3,
    max_num_containers=5,
    label="Microservice 2",
    deamon=False,
)

ms3 = vMicroserviceDeafult(
    cpu=40,
    cpu_limit=80,
    ram=512,
    ram_limit=1024,
    image_size=100,
    volumes=[("test", "test", 100, False), ("test2", "test", 100, True)],
    min_num_containers=3,
    max_num_containers=5,
    label="Microservice 3",
    deamon=False,
)

ns = vNetworkService(
    microservices=[ms1, ms2, ms3],
    links=[(ms1, ms2), (ms2, ms3)],
    entry=ms1,
    exit=ms3,
    label="Network Service 1",
)


def random_process_length():
    return random.randint(10, 50)


def random_packet_size():
    return random.randint(100, 65536)


def random_num_packets():
    return random.randint(5, 10)


sfc = vSFC(
    entry=(ms1, GET),
    exit=(ms3, POST),
    path=[(ms1, ms2, GET), (ms2, ms3, GET)],
    network_service=ns,
    label=f"test",
)

user = vUser()
for i in range(20):
    user.request_sfc(sfc, priority=i, retry=True, backoff=lambda: random.random())

host_monitor = HostMonitor()
workflow_monitor = WorkFlowMonitor()
packet_monitor = PacketMonitor()
ms_monitor = MSMonitor()
req_monitor = RequestMonitor()

simulation.run(10)

host_monitor.df.to_csv("./test_result/host.csv")
packet_monitor.df.to_csv("./test_result/packet.csv")
ms_monitor.df.to_csv("./test_result/ms.csv")
workflow_monitor.df.to_csv("./test_result/workflow.csv")
req_monitor.df.to_csv("./test_result/req.csv")
