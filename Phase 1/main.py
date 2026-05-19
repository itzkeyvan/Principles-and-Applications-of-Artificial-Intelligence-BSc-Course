from environment import Map

def bfs(env):
    initial_state = env.get_start_state()

    # Implement your code here.
    
    # yield ("expand", current_state)
    # yield ("goal", path)
    # yield ("frontier", successor)

    yield ("fail", None)

def dls(env):
    initial_state = env.get_start_state()

    # Implement your code here.
    
    # yield ("reset_visuals", None)
    # yield ("expand", current_state)
    # yield ("goal", path)
    # yield ("frontier", successor)

    yield ("fail", None)

def bds(env):
    initial_state = env.get_start_state()
    goal_state = env.get_goal_state()

    # Implement your code here.
    
    # yield ("expand", current_state)
    # yield ("goal", path)
    # yield ("frontier", successor)

    yield ("fail", None)

def astar(env):
    initial_state = env.get_start_state()
    goal_state = env.get_goal_state()

    # Implement your code here.

    def heuristic(state):
        pass

    def heuristic_bonus(state):
        pass
    
    # yield ("expand", current_state)
    # yield ("goal", path)
    # yield ("frontier", successor)

    yield ("fail", None)

if __name__ == "__main__":
    map = Map(
        search_algorithm=bfs,
        seed=42,
        delay=25
    )
    map.start()