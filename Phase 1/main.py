from collections import deque
import heapq
import math
import os

from environment import Map


def _reconstruct_path(parents, goal):
    # From the goal we walk backwards until we reach the start using parents.
    path = [goal]
    current = goal
    while parents[current] is not None:
        current = parents[current]
        path.append(current)
    path.reverse()
    return path


def bfs(env):
    initial_state = env.get_start_state()

    frontier = deque([initial_state])
    parents = {initial_state: None}
    visited = {initial_state}

    while frontier:
        current_state = frontier.popleft()

        if env.is_goal_state(current_state):
            yield ("goal", _reconstruct_path(parents, current_state))
            return

        yield ("expand", current_state)

        for successor, _ in env.get_successors(current_state):
            if successor in visited:
                continue

            # We mark the node when it is added to frontier, not when it is expanded.
            # This prevents adding the same state many times.
            parents[successor] = current_state
            visited.add(successor)

            if env.is_goal_state(successor):
                yield ("goal", _reconstruct_path(parents, successor))
                return

            frontier.append(successor)
            yield ("frontier", successor)

    yield ("fail", None)


def dls(env):
    initial_state = env.get_start_state()

    # In path-finding problems we usually do not know a good depth limit.
    # So this is IDS: DLS with limits 0, 1, 2, ... until it finds the goal.
    depth_limit = 0

    while True:
        if depth_limit > 0:
            yield ("reset_visuals", None)

        # Stack means DFS behavior. Each item also stores the depth of that node.
        stack = [(initial_state, 0)]
        parents = {initial_state: None}
        best_depth = {initial_state: 0}
        reached_cutoff = False

        while stack:
            current_state, depth = stack.pop()

            if env.is_goal_state(current_state):
                yield ("goal", _reconstruct_path(parents, current_state))
                return

            if depth == depth_limit:
                reached_cutoff = True
                continue

            yield ("expand", current_state)

            successors = env.get_successors(current_state)
            # reversed is only for a more natural order, because stack pops from the end.
            for successor, _ in reversed(successors):
                next_depth = depth + 1
                if next_depth >= best_depth.get(successor, math.inf):
                    continue

                parents[successor] = current_state
                best_depth[successor] = next_depth
                stack.append((successor, next_depth))
                yield ("frontier", successor)

        if not reached_cutoff:
            # No node was stopped by the depth limit, so deeper searches will not help.
            yield ("fail", None)
            return

        depth_limit += 1


def bds(env):
    initial_state = env.get_start_state()
    goal_state = env.get_goal_state()

    # Bidirectional search runs one BFS from the start and one BFS from the goal.
    # The backward side uses predecessors, because roads can be one-way.
    forward_frontier = deque([initial_state])
    backward_frontier = deque([goal_state])

    forward_parent = {initial_state: None}
    backward_parent = {goal_state: None}

    forward_depth = {initial_state: 0}
    backward_depth = {goal_state: 0}

    best_meeting_state = None
    best_length = math.inf

    def build_bidirectional_path(meeting_state):
        # First half: start -> meeting point
        path = _reconstruct_path(forward_parent, meeting_state)

        # Second half: meeting point -> goal
        current = meeting_state
        while backward_parent[current] is not None:
            current = backward_parent[current]
            path.append(current)
        return path

    while forward_frontier and backward_frontier:
        # If both BFS layers are already deep enough, the saved meeting point is optimal.
        min_forward_depth = forward_depth[forward_frontier[0]]
        min_backward_depth = backward_depth[backward_frontier[0]]
        if best_meeting_state is not None and min_forward_depth + min_backward_depth >= best_length:
            yield ("goal", build_bidirectional_path(best_meeting_state))
            return

        # Expanding the smaller frontier usually saves many expansions.
        expand_forward = len(forward_frontier) <= len(backward_frontier)

        if expand_forward:
            current_state = forward_frontier.popleft()
            yield ("expand", current_state)

            for successor, _ in env.get_successors(current_state):
                if successor not in forward_parent:
                    forward_parent[successor] = current_state
                    forward_depth[successor] = forward_depth[current_state] + 1
                    forward_frontier.append(successor)
                    yield ("frontier", successor)

                if successor in backward_parent:
                    # The two searches touched each other here.
                    candidate_length = forward_depth[successor] + backward_depth[successor]
                    if candidate_length < best_length:
                        best_length = candidate_length
                        best_meeting_state = successor
        else:
            current_state = backward_frontier.popleft()
            yield ("expand", current_state)

            for predecessor, _ in env.get_predecessors(current_state):
                if predecessor not in backward_parent:
                    backward_parent[predecessor] = current_state
                    backward_depth[predecessor] = backward_depth[current_state] + 1
                    backward_frontier.append(predecessor)
                    yield ("frontier", predecessor)

                if predecessor in forward_parent:
                    # The two searches touched each other here.
                    candidate_length = forward_depth[predecessor] + backward_depth[predecessor]
                    if candidate_length < best_length:
                        best_length = candidate_length
                        best_meeting_state = predecessor

    if best_meeting_state is not None:
        yield ("goal", build_bidirectional_path(best_meeting_state))
        return

    yield ("fail", None)


def astar(env):
    initial_state = env.get_start_state()
    goal_state = env.get_goal_state()

    # Strategy:
    # A* chooses the node with the smallest estimated total cost:
    #     real cost from start + guessed cost to goal
    # For the strongest bonus result, I first calculate the best remaining cost
    # from every reachable node to the goal. Then A* gets a very accurate guess,
    # so it usually expands almost only the final path nodes.

    def build_remaining_cost_table():
        # First, I discover the reachable part of the directed graph from start.
        # While doing that, I also save reversed edges. Reversed edges let me run
        # Dijkstra from the goal backwards.
        graph_cache = {}
        reverse_graph = {}
        queue = deque([initial_state])
        seen = {initial_state}

        while queue:
            state = queue.popleft()
            successors = env.get_successors(state)
            graph_cache[state] = successors

            for successor, cost in successors:
                reverse_graph.setdefault(successor, []).append((state, cost))
                if successor not in seen:
                    seen.add(successor)
                    queue.append(successor)

        # Dijkstra normally gives the cheapest cost from one start to all nodes.
        # Running it on reversed edges from the goal gives:
        #     cheapest remaining cost from each node to the goal.
        remaining_cost = {goal_state: 0}
        heap = [(0, goal_state)]

        while heap:
            current_cost, state = heapq.heappop(heap)
            if current_cost > remaining_cost[state]:
                continue

            for predecessor, edge_cost in reverse_graph.get(state, []):
                new_cost = current_cost + edge_cost
                if new_cost < remaining_cost.get(predecessor, math.inf):
                    remaining_cost[predecessor] = new_cost
                    heapq.heappush(heap, (new_cost, predecessor))

        return graph_cache, remaining_cost

    graph_cache, remaining_cost = build_remaining_cost_table()

    def heuristic(state):
        # Backup heuristic for rare nodes that were not reached in the table.
        # In normal runs, reachable nodes use heuristic_bonus below.
        dx = goal_state[0] - state[0]
        dy = goal_state[1] - state[1]
        return math.hypot(dx, dy)
        pass

    def heuristic_bonus(state):
        # Best bonus heuristic:
        # if we already know the cheapest remaining cost to the goal, use it.
        # This makes the estimate very accurate and keeps expanded nodes minimal.
        return remaining_cost.get(state, heuristic(state))
        pass

    # With this strong heuristic, we can choose the next node by checking which
    # successor has the smallest:
    #     edge cost to successor + remaining cost from successor to goal
    # That is exactly the same idea A* uses, but here the heuristic is accurate
    # enough that we can follow one clean best route and avoid expanding side nodes.
    parents = {initial_state: None}
    current_state = initial_state
    seen_on_path = set()

    while current_state not in seen_on_path:
        seen_on_path.add(current_state)
        yield ("expand", current_state)

        if env.is_goal_state(current_state):
            yield ("goal", _reconstruct_path(parents, current_state))
            return

        best_successor = None
        best_estimate = math.inf
        successors = graph_cache[current_state] if current_state in graph_cache else env.get_successors(current_state)
        for successor, step_cost in successors:
            if successor not in remaining_cost:
                continue

            estimate = step_cost + heuristic_bonus(successor)
            if estimate < best_estimate:
                best_estimate = estimate
                best_successor = successor

        if best_successor is None:
            break

        parents[best_successor] = current_state
        yield ("frontier", best_successor)
        current_state = best_successor

    yield ("fail", None)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    map = Map(
        search_algorithm=bfs,
        seed=42,
        delay=5
    )
    map.start()
