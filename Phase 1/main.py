from collections import deque
import heapq
import itertools
import math
import os

from environment import Map


def _reconstruct_path(parents, goal):
    # parents keeps "where did I come from?" for each node.
    # So from the goal we walk backwards until we reach the start.
    path = [goal]
    current = goal
    while parents[current] is not None:
        current = parents[current]
        path.append(current)
    path.reverse()
    return path


def bfs(env):
    initial_state = env.get_start_state()

    # BFS uses a normal queue: first node that enters, first node that leaves.
    # This makes the first found answer have the minimum number of nodes/edges.
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
    # So this is actually IDS: DLS with limits 0, 1, 2, ... until it finds the goal.
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


def Astar(env):
    initial_state = env.get_start_state()
    goal_state = env.get_goal_state()

    def heuristic(state):
        # Straight-line distance is a simple admissible heuristic:
        # it never overestimates the actual road distance.
        return math.hypot(goal_state[0] - state[0], goal_state[1] - state[1])

    # heap item: (f = g + h, h, tie_breaker, state)
    # tie_breaker avoids Python comparing states when the numbers are equal.
    counter = itertools.count()
    frontier = [(heuristic(initial_state), heuristic(initial_state), next(counter), initial_state)]
    parents = {initial_state: None}
    best_cost = {initial_state: 0}
    expanded = set()
    frontier_states = {initial_state}

    while frontier:
        _, _, _, current_state = heapq.heappop(frontier)
        current_cost = best_cost[current_state]

        if current_state in expanded:
            continue

        frontier_states.discard(current_state)

        if env.is_goal_state(current_state):
            yield ("goal", _reconstruct_path(parents, current_state))
            return

        expanded.add(current_state)
        yield ("expand", current_state)

        for successor, step_cost in env.get_successors(current_state):
            new_cost = current_cost + step_cost
            if new_cost >= best_cost.get(successor, math.inf):
                continue

            # Found a cheaper way to reach successor.
            parents[successor] = current_state
            best_cost[successor] = new_cost
            h_value = heuristic(successor)
            priority = new_cost + h_value
            heapq.heappush(frontier, (priority, h_value, next(counter), successor))

            if successor not in expanded and successor not in frontier_states:
                frontier_states.add(successor)
                yield ("frontier", successor)

    yield ("fail", None)


if __name__ == "__main__":
    # environment.py loads map.png, nodes.json and edges.json with relative paths.
    # This makes the program work even if the IDE runs it from another folder.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    map = Map(
        search_algorithm=Astar,
        seed=42,
        delay=0
    )
    map.start()
