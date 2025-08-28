# algo.py
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

# Type alias: A seat is identified by (row, col)
Seat = Tuple[int, int]

# -------------------------------
# Build grid graph adjacency
# -------------------------------
def build_grid_graph(rows: int, cols: int) -> Dict[Seat, List[Seat]]:
    adj = {(r, c): [] for r in range(rows) for c in range(cols)}
    for r in range(rows):
        for c in range(cols):
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:  # N, S, W, E neighbors
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    adj[(r, c)].append((nr, nc))
    return adj

# -------------------------------
# Greedy coloring
# -------------------------------
def greedy_assign(adj: Dict[Seat, List[Seat]], subject_counts: Dict[str, int]) -> Optional[Dict[Seat, str]]:
    # order seats by degree descending
    order = sorted(adj.keys(), key=lambda n: len(adj[n]), reverse=True)
    assignment: Dict[Seat, str] = {}
    remaining = subject_counts.copy()

    for node in order:
        neighbor_subjects = {assignment[n] for n in adj[node] if n in assignment}
        candidates = [s for s, c in remaining.items() if c > 0 and s not in neighbor_subjects]
        if not candidates:
            return None
        # pick subject with most students left
        best = max(candidates, key=lambda s: remaining[s])
        assignment[node] = best
        remaining[best] -= 1

    if any(v != 0 for v in remaining.values()):
        return None
    return assignment

# -------------------------------
# Backtracking CSP with MRV + forward checking
# -------------------------------
def backtracking_csp(adj: Dict[Seat, List[Seat]], subject_counts: Dict[str, int]) -> Optional[Dict[Seat, str]]:
    nodes = list(adj.keys())
    degree = {n: len(adj[n]) for n in nodes}
    domains: Dict[Seat, Set[str]] = {n: {s for s, c in subject_counts.items() if c > 0} for n in nodes}
    remaining = subject_counts.copy()
    assignment: Dict[Seat, str] = {}

    def select_unassigned_var() -> Seat:
        unassigned = [n for n in nodes if n not in assignment]
        # MRV (min remaining values), then degree heuristic
        return min(unassigned, key=lambda n: (len(domains[n]), -degree[n]))

    def consistent(node: Seat, subj: str) -> bool:
        for nb in adj[node]:
            if nb in assignment and assignment[nb] == subj:
                return False
        return True

    def forward_check(node: Seat, subj: str, removed: List[Tuple[Seat, str]]) -> bool:
        for nb in adj[node]:
            if nb in assignment:
                continue
            if subj in domains[nb]:
                domains[nb].remove(subj)
                removed.append((nb, subj))
                if not domains[nb]:
                    return False
        return True

    def restore(removed: List[Tuple[Seat, str]]) -> None:
        for nb, subj in removed:
            domains[nb].add(subj)

    def backtrack() -> bool:
        if len(assignment) == len(nodes):
            return all(v == 0 for v in remaining.values())
        node = select_unassigned_var()
        for subj in sorted(domains[node], key=lambda s: remaining[s], reverse=True):
            if remaining[subj] == 0:
                continue
            if not consistent(node, subj):
                continue
            assignment[node] = subj
            remaining[subj] -= 1
            removed: List[Tuple[Seat, str]] = []
            if forward_check(node, subj, removed) and backtrack():
                return True
            restore(removed)
            remaining[subj] += 1
            del assignment[node]
        return False

    return assignment if backtrack() else None

# -------------------------------
# Public function for Flask app
# -------------------------------
def generate_seating(rows: int, cols: int, students: List[Dict[str, str]], algo: str = "auto") -> Optional[Dict[Seat, Optional[Dict[str, str]]]]:
    """
    Generate a seating map: (row, col) -> student dict or None (empty seat).
    Allows len(students) <= rows*cols.
    """
    capacity = rows * cols
    n = len(students)

    # Too many students
    if n > capacity:
        return None

    # count students per subject
    counts: Dict[str, int] = {}
    for s in students:
        counts[s["subject"]] = counts.get(s["subject"], 0) + 1

    adj = build_grid_graph(rows, cols)
    assign: Optional[Dict[Seat, str]] = None

    if algo in ("auto", "greedy"):
        assign = greedy_assign(adj, counts)
    if assign is None and algo in ("auto", "backtracking"):
        assign = backtracking_csp(adj, counts)

    if assign is None:
        return None

    # distribute students into seats
    pools: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for s in students:
        pools[s["subject"]].append(s)
    for k in pools:
        pools[k].sort(key=lambda x: x["id"])

    seat_map: Dict[Seat, Optional[Dict[str, str]]] = {}
    for seat, subj in assign.items():
        if pools[subj]:  # assign student
            seat_map[seat] = pools[subj].pop(0)
        else:
            seat_map[seat] = None  # leave empty

    return seat_map
