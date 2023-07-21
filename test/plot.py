from typing import List
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def plot(
    file: str,
    x_axis: str|List[str],
    y_axis: str|List[str],
    target_field: str,
    targets: List[str],
    xlabel: str,
    ylabel: str,
    title:str,
    kind: str,
    figname: str,
):
    raw_df = pd.read_csv(file)
    fig, ax = plt.subplots()
    for target in targets:
        if isinstance(x_axis, str) and isinstance(y_axis, str):
            df = pd.DataFrame()
            df[x_axis] = raw_df[raw_df[target_field] == target][x_axis].values
            df[target] = raw_df[raw_df[target_field] == target][y_axis].values
            if kind == "scatter":
                ax.scatter(df[x_axis], df[target], label=target)
            elif kind == "line":
                ax.plot(df[x_axis], df[target], label=target)
        elif isinstance(x_axis, list) and isinstance(y_axis, list):
            if len(x_axis) != len(y_axis):
                raise ValueError("x_axis and y_axis must have the same length")
            else:
                for i in range(len(x_axis)):
                    df = pd.DataFrame()
                    df[x_axis[i]] = raw_df[raw_df[target_field] == target][x_axis[i]].values
                    df[target] = raw_df[raw_df[target_field] == target][y_axis[i]].values
                    if kind == "scatter":
                        ax.scatter(df[x_axis[i]], df[target], label=target)
                    elif kind == "line":
                        ax.plot(df[x_axis[i]], df[target], label=target)
        else:
            raise ValueError("x_axis and y_axis must be both str or list")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(targets)
    ax.grid()
    ax.set_title(title)
    fig.savefig(figname)

plot(
    file="./test_result/host.csv",
    x_axis="time",
    y_axis="cpu_util",
    target_field="host_label",
    targets=["Host 0", "Host 1"],
    xlabel="Time (s)",
    ylabel="CPU Utilization (%)",
    kind="scatter",
    figname="./test_result/host_cpu_util.pdf",  
    title="CPU Utilization of Hosts", 
)

plot(
    file="./test_result/host.csv",
    x_axis="time",
    y_axis="ram_util",
    target_field="host_label",
    targets=["Host 0", "Host 1"],
    xlabel="Time (s)",
    ylabel="RAM Utilization (%)",
    kind="scatter",
    figname="./test_result/host_ram_util.pdf",
    title="RAM Utilization of Hosts",
)

plot(
    file="./test_result/host.csv",
    x_axis="ram_util",
    y_axis="cpu_util",
    target_field="host_label",
    targets=["Host 0", "Host 1"],
    xlabel="RAM Utilization (%)",
    ylabel="CPU Utilization (%)",
    kind="scatter",
    figname="./test_result/host_ram_cpu.pdf",  
    title="Host RAM Utilization vs. CPU Utilization",
)

plot(
    file="./test_result/ms.csv",
    x_axis="time",
    y_axis="cpu_util",
    target_field="ms",
    targets=["AMF", "AUSF", "UDR","SMF", "UDM", "UPF","PCF"],
    xlabel="Time (s)",
    ylabel="CPU Utilization (%)",
    kind="scatter",
    figname="./test_result/ms_cpu_util.pdf",
    title="CPU Utilization of Microservices",
)

plot(
    file="./test_result/ms.csv",
    x_axis="time",
    y_axis="ram_util",
    target_field="ms",
    targets=["AMF", "AUSF", "UDR","SMF", "UDM", "UPF","PCF"],
    xlabel="Time (s)",
    ylabel="RAM Utilization (%)",
    kind="scatter",
    figname="./test_result/ms_ram_util.pdf",
    title="RAM Utilization of Microservices",
)

plot(
    file="./test_result/ms.csv",
    x_axis="ram_util",
    y_axis="cpu_util",
    target_field="ms",
    targets=["AMF", "AUSF", "UDR","SMF", "UDM", "UPF","PCF"],
    xlabel="RAM Utilization (%)",
    ylabel="CPU Utilization (%)",
    kind="scatter",
    figname="./test_result/ms_ram_cpu.pdf",
    title="Microservices RAM Utilization vs. CPU Utilization",
)
