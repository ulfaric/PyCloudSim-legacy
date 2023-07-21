from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Tuple, Union, Callable
import networkx as nx
from networkx.drawing.layout import spring_layout
from networkx.drawing.nx_pylab import (
    draw_networkx_nodes,
    draw_networkx_edges,
    draw_networkx_labels,
)
import matplotlib.pyplot as plt

from .v_entity import Entity
from .v_virtual_entity import VirtualEntity
from ..core import simulation
from .v_microservice import vMicroservice


class vNetworkService(VirtualEntity):
    def __init__(
        self,
        microservices: List[vMicroservice],
        links: List[Tuple[vMicroservice, vMicroservice]],
        entry: Optional[vMicroservice | List[vMicroservice]],
        exit: Optional[vMicroservice | List[vMicroservice]],
        at: Union[int, float, Callable] = simulation.now,
        after: Optional[Entity | List[Entity]] = None,
        label: Optional[str] = None,
    ):
        """Create a vNetworkService

        Args:
            microservices (List[vMicroservice]): the list of engaged microservices.
            links (List[Tuple[vMicroservice, vMicroservice]]): the links of the microservices.
            entry (Optional[vMicroservice  |  List[vMicroservice]]): the entry point of the network service, aka the microservice that will accept user's request at the beginning.
            exit (Optional[vMicroservice  |  List[vMicroservice]]): _description_
            at (Union[int, float, Callable], optional): _description_. Defaults to simulation.now.
            after (Optional[Entity  |  List[Entity]], optional): _description_. Defaults to None.
            label (Optional[str], optional): _description_. Defaults to None.
        """
        super().__init__(at=at, after=after, label=label)

        self._microservices = microservices
        self._links = links
        self._graph = nx.DiGraph()
        self.graph.add_nodes_from(self.microservices)
        for link in self.links:
            self.graph.add_edge(link[0], link[1])
            self.graph.add_edge(link[1], link[0])

        if isinstance(entry, list):
            self._entry = list()
            for e in entry:
                if e in self.graph.nodes:
                    self._entry.append(e)
                else:
                    raise ValueError(
                        f"vMicroservice {e.label} is not in the topology of vNetworkService {self.label}"
                    )
        elif isinstance(entry, vMicroservice):
            if entry in self.graph.nodes:
                self._entry = entry
            else:
                raise ValueError(
                    f"vMicroservice {entry.label} is not in the topology of vNetworkService {self.label}"
                )

        if isinstance(exit, list):
            self._exit = list()
            for e in exit:
                if e in self.graph.nodes:
                    self._exit.append(e)
                else:
                    raise ValueError(
                        f"vMicroservice {e.label} is not in the topology of vNetworkService {self.label}"
                    )
        elif isinstance(exit, vMicroservice):
            if exit in self.graph.nodes:
                self._exit = exit
            else:
                raise ValueError(
                    f"vMicroservice {exit.label} is not in the topology of vNetworkService {self.label}"
                )

        simulation.NETWORKSERVICES.append(self)

    def termination(self):
        """Terminate the vNetworkService and all its microservices and SFCS"""
        super().termination()
        for ms in self.microservices:
            ms.terminate()
        for sfc in simulation.SFCS:
            if sfc.network_service is self:
                sfc.terminate()

    def draw(self, save: bool = False):
        """Plot the topology of the vNetworkService"""
        fig, ax = plt.subplots()
        label_mapping = dict()
        for ms in self.microservices:
            label_mapping[ms] = ms.label
        pos = spring_layout(self.graph)
        for node in self.graph.nodes:
            draw_networkx_nodes(
                self.graph, pos, ax=ax, nodelist=[node], node_color="tab:green"
            )
        for edge in self.graph.edges:
            draw_networkx_edges(
                self.graph, pos, ax=ax, edgelist=[edge], edge_color="tab:gray"
            )
        if isinstance(self.entry, list):
            draw_networkx_nodes(
                self.graph, pos, ax=ax, nodelist=self.entry, node_color="tab:red"
            )
        elif isinstance(self.entry, vMicroservice):
            draw_networkx_nodes(
                self.graph, pos, ax=ax, nodelist=[self.entry], node_color="tab:red"
            )
        if isinstance(self.exit, list):
            draw_networkx_nodes(
                self.graph, pos, ax=ax, nodelist=self.exit, node_color="tab:blue"
            )
        elif isinstance(self.exit, vMicroservice):
            draw_networkx_nodes(
                self.graph, pos, ax=ax, nodelist=[self.exit], node_color="tab:blue"
            )
        draw_networkx_labels(self.graph, pos, labels=label_mapping, ax=ax)
        plt.show()
        if save:
            fig.savefig(f"{self.label}.png")

    @property
    def microservices(self) -> List[vMicroservice]:
        """The list of microservices engaged in the vNetworkService"""
        return self._microservices

    @property
    def links(self) -> List[Tuple[vMicroservice, vMicroservice]]:
        """The links of the microservices"""
        return self._links

    @property
    def graph(self) -> nx.DiGraph:
        """The topology of the vNetworkService"""
        return self._graph

    @property
    def entry(self) -> Optional[vMicroservice | List[vMicroservice]]:
        """The entry point of the vNetworkService"""
        return self._entry

    @property
    def exit(self) -> Optional[vMicroservice | List[vMicroservice]]:
        """The exit point of the vNetworkService"""
        return self._exit
