from PyCloudSim.entity import vMicroserviceDeafult, vHost, vNetworkService, vSFC, vUser
from PyCloudSim.monitor import (
    HostMonitor,
    PacketMonitor,
    MSMonitor,
    WorkFlowMonitor,
    RequestMonitor,
    UserRequestMonitor,
)
from PyCloudSim.core import simulation
from PyCloudSim.util import *
import random
from Akatosh import event

default_settings()
initiate_topology()
amf = vMicroserviceDeafult(
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    label="AMF",
    min_num_containers=1,
    max_num_containers=1,
)

ausf = vMicroserviceDeafult(
    label="AUSF",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=1,
)

udm = vMicroserviceDeafult(
    label="UDM",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=1,
)

smf = vMicroserviceDeafult(
    label="SMF",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=1,
)

udr = vMicroserviceDeafult(
    label="UDR",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=1,
)


pcf = vMicroserviceDeafult(
    label="PCF",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=1,
)

upf = vMicroserviceDeafult(
    label="UPF",
    cpu=50,
    cpu_limit=100,
    ram=128,
    ram_limit=256,
    image_size=100,
    min_num_containers=1,
    max_num_containers=3,
)

sfc_1 = vSFC(
    label="request_access",
    entry=(amf, POST),
    path=[(amf, ausf, POST)],
    at=0,
)

sfc_2 = vSFC(
    label="notice_udm",
    path=[(ausf, udm, POST)],
    internal=True,
)

sfc_3 = vSFC(
    label="config_pcf",
    path=[(udm, udr, POST), (udr, pcf, POST)],
    internal=True,
)

sfc_4 = vSFC(
    label="config_smf",
    path=[(udm, smf, POST)],
    internal=True,
)

sfc_5 = vSFC(
    label="notice_ausf",
    path=[(udm, ausf, POST)],
    internal=True,
)

sfc_6 = vSFC(
    label="grant_access",
    exit=(amf, POST),
    path=[(ausf, amf, POST)],
)

sfc_7 = vSFC(
    label="access_internet",
    entry=(upf, GET),
    exit=(upf, POST),
)

for i in range(2):
    vHost(
        ram=4,
        rom=1024,
        ipc=1,
        frequency=4000,
        num_cpu_cores=1,
        at=0,
        label=f"Host {i}",
    )
    
for _ in range(10):
    user = vUser()
    flow1 = user.request_sfc(sfc_1)
    flow2 = user.request_sfc(sfc_2,after=flow1)
    flow3 = user.request_sfc(sfc_3,after=flow2)
    flow4 = user.request_sfc(sfc_4,after=flow3)
    flow5 = user.request_sfc(sfc_5,after=flow4)
    flow6 = user.request_sfc(sfc_6,after=flow5)
    flow7 = user.request_sfc(sfc_7,after=flow6, num_packets=100, packet_size=lambda: random.randint(100, 65536))

host_monitor = HostMonitor()
workflow_monitor = WorkFlowMonitor()
packet_monitor = PacketMonitor()
ms_monitor = MSMonitor()
req_monitor = RequestMonitor()
user_request_monitor = UserRequestMonitor()

simulation.run(10)

host_monitor.df.to_csv("./test_result/host.csv")
packet_monitor.df.to_csv("./test_result/packet.csv")
ms_monitor.df.to_csv("./test_result/ms.csv")
workflow_monitor.df.to_csv("./test_result/workflow.csv")
req_monitor.df.to_csv("./test_result/req.csv")
user_request_monitor.df.to_csv("./test_result/user_req.csv")
