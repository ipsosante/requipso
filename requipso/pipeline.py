# pyright: reportOptionalContextManager=false

import datetime
from typing import Any, Generator, Optional, Self

import networkx as nx
import polars as pl
from graphviz import Digraph  # type: ignore

from requipso.data import Data
from requipso.pipes.base import BaseBlock, OutputType


class Pipeline:
    def __init__(
        self: Self,
        initial_text: str = "Patients",
        reference_date: datetime.datetime | None = None,
    ) -> None:
        self.steps: nx.DiGraph = nx.DiGraph()
        self.initial_text = initial_text
        self.initial_n: int | None = None
        self.source_step: BaseBlock | None = None
        self.steps_names: dict[str, BaseBlock] = dict()
        self.steps_results: dict[str, dict[str, Any]]
        self.reference_date = reference_date
        self.last_addded_step: BaseBlock | None = None

    def add_step(
        self,
        step: BaseBlock,
        text: str | None = None,
        excluded_text: str | None = None,
        parent_step: BaseBlock | str | None = None,
    ) -> None:
        if (self.steps.number_of_nodes() > 0) and parent_step is None:
            parent_step = self.last_addded_step

        if (self.steps.number_of_nodes() == 0) and parent_step is not None:
            raise ValueError("A parent step is not permitted for the first step")

        if step.name in self.steps_names.keys():
            raise ValueError(f"Step {step.name} already exists")

        self.steps_names[step.name] = step

        if isinstance(parent_step, str):
            parent_step = self.steps_names.get(parent_step)
            if parent_step is None:
                raise ValueError(f"Parent step {parent_step} not found")

        if self.source_step is None:
            self.source_step = step

        self.steps.add_node(
            step,
            idx=self.steps.number_of_nodes(),
            name=step.name,
            output_patients=None,  # Will store the pl.Series containing the patients that passed the step
            text=text,
            excluded_text=excluded_text,
        )
        if parent_step is not None:
            if parent_step not in self.steps.nodes:
                raise ValueError(f"Parent step {parent_step.name} not found")
            self.steps.add_edge(parent_step, step)

        self.last_addded_step = step

    def graph(self, save_name: str) -> Digraph:
        return dag_to_consort_flowchart(
            self.steps,
            name=save_name,
            source_text=self.initial_text,
            source_n=self.initial_n,
            render_path=save_name,
        )

    def reset_output_patients(self):
        # TODO
        pass

    def iter_run(self, data: Data) -> Generator[tuple[str, int], None, None]:
        """Yield ``(step_name, n_remaining)`` after executing each step.

        This generator form lets the caller wrap the iteration with a progress
        bar (e.g. ``mo.status.progress_bar``) so the UI updates correctly
        between each yield.
        """
        self.steps_results = dict()

        for step in nx.dfs_preorder_nodes(self.steps, source=self.source_step):
            parents = list[BaseBlock](self.steps.predecessors(step))
            if not parents:
                input_patients = None
            else:
                parent = parents[0]
                input_patients = (
                    data.all_results[parent.name]["post"]
                    .filter(pl.col(parent.name))
                    .get_column("patient_id")
                    .unique()
                )

            output_type = OutputType.BOOLEAN
            if output_type != OutputType.BOOLEAN:
                raise ValueError(
                    f"Step {step.name} has output type {output_type}, expected BOOLEAN"
                )

            data = step.execute(
                data,
                patient_ids=input_patients,
                reference_date=self.reference_date,
            )

            output_patients = (
                data.all_results[step.name]["post"]
                .filter(pl.col(step.name))
                .get_column("patient_id")
                .unique()
            )

            if step.has_date:
                data.all_results[step.name]["dates"] = data.all_results[step.name][
                    "dates"
                ].filter(pl.col("patient_id").is_in(output_patients))

            self.steps.nodes[step]["n"] = len(output_patients)

            self.steps_results[step.name] = {
                "n": len(output_patients),
            }

            if not parents:
                self.initial_n = data.patient.n_unique()

            yield step.name, len(output_patients)

    def run(self, data: Data) -> Data:
        # simple iter with iter_run
        for step_name, n in self.iter_run(data):
            pass
        return data


def _node_id(node: Any) -> str:
    """Get a stable, clean string ID for a node."""
    if hasattr(node, "name"):
        return str(node.name)
    return str(id(node))


def dag_to_consort_flowchart(
    G: nx.DiGraph,
    *,
    name: str = "consort",
    fmt: str = "png",
    fontname: str = "Helvetica",
    fontsize: str = "11",
    nodesep: str = "0.4",
    ranksep: str = "0.5",
    source_text: Optional[str] = None,
    source_n: Optional[int | str] = None,
    render_path: Optional[str] = None,
) -> Digraph:
    """
    Build a CONSORT-style inclusion flowchart from a NetworkX DAG.

    Classical CONSORT layout:
      - Single vertical main chain (top → bottom)
      - "Excluded" boxes branch off to the RIGHT, placed BEFORE (above)
        their corresponding node via a T-junction on the incoming edge
      - Splits (randomisation arms) place children side-by-side on the same rank

    Parameters:
      source_text : label for a virtual first node displayed above the root
      source_n    : sample size shown on the virtual first node

    Node attributes (on the NetworkX graph):
      - "text": str   – main label text
      - "n": int|str  – sample size, shown as (n=…)
      - "excluded_text": str  – optional; text for the excluded side-box
    """
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError("G must be a DAG.")

    dot = Digraph(name=name, format=fmt)
    dot.attr(rankdir="TB", splines="ortho", nodesep=nodesep, ranksep=ranksep)
    dot.attr("node", shape="box", style="rounded", fontname=fontname, fontsize=fontsize)
    dot.attr(
        "edge",
        fontname=fontname,
        fontsize=str(max(int(fontsize) - 2, 8)),
        arrowsize="0.8",
    )

    # --- helpers ---
    def _label(node: Any) -> str:
        d = G.nodes[node]
        text = str(d.get("text", str(node)))
        n = d.get("n")
        return f"{text}\n(n={n})" if n is not None and str(n).strip() else text

    def _safe_int(v: Any) -> Optional[int]:
        """Try to interpret v as int; return None on failure."""
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def _excl_label(excl_text: str, parent_n: Any, child_n: Any) -> str:
        """Build the excluded-box label, with (n=…) when computable."""
        pn = _safe_int(parent_n)
        cn = _safe_int(child_n)
        label = f"Excluded\n{excl_text}"
        if pn is not None and cn is not None:
            label += f"\n(n={pn - cn})"
        return label

    def _excl_node(node_id: str, label: str) -> None:
        dot.node(
            node_id,
            label,
            shape="box",
            style="rounded,dashed",
            fontname=fontname,
            fontsize=fontsize,
        )

    # 1) Declare all main nodes
    for u in G.nodes:
        dot.node(_node_id(u), _label(u))

    topo = list(nx.topological_sort(G))
    excluded_drawn: set = set()

    # 2) Virtual source node + root exclusion handling
    root = topo[0]
    root_id = _node_id(root)
    root_excl = G.nodes[root].get("excluded_text")

    # Build the virtual source node label
    if source_text:
        src_label = source_text
        if source_n is not None and str(source_n).strip():
            src_label += f"\n(n={source_n})"
        dot.node("_source", src_label)
        upstream_id = "_source"
        upstream_n = source_n
    else:
        upstream_id = None
        upstream_n = None

    if root_excl:
        excluded_drawn.add(root)
        mid = f"_mid_{root_id}"
        exc = f"_exc_{root_id}"

        dot.node(mid, "", shape="point", width="0", height="0")
        _excl_node(exc, _excl_label(root_excl, upstream_n, G.nodes[root].get("n")))

        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(mid)
            s.node(exc)

        if upstream_id:
            dot.edge(upstream_id, mid, arrowhead="none")
        dot.edge(mid, exc)
        dot.edge(mid, root_id)
    elif upstream_id:
        dot.edge(upstream_id, root_id)

    # 3) Walk in topological order — exclusion boxes go on the
    #    CHILD's incoming edge (before the child), not the parent's outgoing edge.
    for u in topo:
        children = list(G.successors(u))
        if not children:
            continue

        uid = _node_id(u)
        parent_n = G.nodes[u].get("n")

        # --- CASE A: single child (linear chain) ---
        if len(children) == 1:
            child = children[0]
            cid = _node_id(child)
            child_excl = (
                G.nodes[child].get("excluded_text")
                if child not in excluded_drawn
                else None
            )

            if child_excl:
                excluded_drawn.add(child)
                mid = f"_mid_{cid}"
                exc = f"_exc_{cid}"

                dot.node(mid, "", shape="point", width="0", height="0")
                _excl_node(
                    exc,
                    _excl_label(child_excl, parent_n, G.nodes[child].get("n")),
                )
                with dot.subgraph() as s:
                    s.attr(rank="same")
                    s.node(mid)
                    s.node(exc)

                dot.edge(uid, mid, arrowhead="none")
                dot.edge(mid, exc)
                dot.edge(mid, cid)
            else:
                dot.edge(uid, cid)

        # --- CASE B: multiple children (split / randomisation) ---
        else:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for v in children:
                    s.node(_node_id(v))

            child_mids: dict = {}
            for child in children:
                cid = _node_id(child)
                child_excl = (
                    G.nodes[child].get("excluded_text")
                    if child not in excluded_drawn
                    else None
                )
                if child_excl:
                    excluded_drawn.add(child)
                    mid = f"_mid_{cid}"
                    exc_id = f"_exc_{cid}"
                    dot.node(mid, "", shape="point", width="0", height="0")
                    _excl_node(
                        exc_id,
                        _excl_label(child_excl, parent_n, G.nodes[child].get("n")),
                    )
                    child_mids[child] = (mid, exc_id)

            if child_mids:
                with dot.subgraph() as s:
                    s.attr(rank="same")
                    for mid, exc_id in child_mids.values():
                        s.node(mid)
                        s.node(exc_id)

            for child in children:
                cid = _node_id(child)
                if child in child_mids:
                    mid, exc_id = child_mids[child]
                    dot.edge(uid, mid, arrowhead="none")
                    dot.edge(mid, exc_id)
                    dot.edge(mid, cid)
                else:
                    dot.edge(uid, cid)

    if render_path:
        dot.render(render_path, cleanup=True)

    return dot
