from .base import GameWrapper
from .utils.zelda_utils import *
from .utils.zelda_utils import TILE_SIZE
from datetime import timedelta
import time

class ZeldaALTTP(GameWrapper):

    def __init__(self, 
                reward_scale = 1.0,
                explore_weight = 2.0,          
                revisit_weight = -0.05,         
                area_discovery_weight = 10.0,   
                rupee_weight = 0.5,            
                health_weight = 0.5,            
                sword_weight = 10.0,            
                enemies_killed_weight = 2.0,
                small_key_weight = 5.0
        ):
        # general variables
        self._env_start_time = time.time()
        self.reward_scale = reward_scale
        self._prev_state = None
        self._prev_reward = 0.0
        self.last_reward_components = {}

        #rupee weight   
        self.rupee_weight = rupee_weight

        #health weight
        self.health_weight = health_weight
        self.died_count = 0
        self.total_deaths = 0  

        #explore weight
        self.explore_weight = explore_weight
        self.seen_coords = {}
        self.revisit_weight = revisit_weight
        self.area_discovery_weight = area_discovery_weight
        self.discovered_areas = set()
        self.area_discovery_timestamps = {}

        # combat weight
        self.sword_weight = sword_weight
        self._prev_sword = 0
        self._sword_obtained = False
        self.sword_discovery_timestamp = None
        self.enemies_killed_weight = enemies_killed_weight
        self.total_enemies_killed = 0  

        # Small key weight
        self.small_key_weight = small_key_weight
        self.total_small_keys = 0  
        
        

    def game_state(self, gba):
        return {
            "health": read_player_health(gba),
            "rupees": read_rupees(gba),
            "coords": self.get_player_coords(gba),
            "area": get_area_description(gba),
            "sword": read_sword(gba),
            "enemies_killed": read_enemies_killed(gba),
            "explored_locations": len(self.seen_coords),
            "small_keys": read_small_keys(gba),
        }

    def persist_state_data(self, state):
        self._prev_sword = state["sword"]
        self._sword_obtained = self._prev_sword > 0

    def get_player_coords(self, gba):
        x, y = read_player_xy(gba)
        tile_x = x // TILE_SIZE
        tile_y = y // TILE_SIZE
        area = get_area_description(gba)
        return (x, y, tile_x, tile_y, area)

    def update_seen_coords(self, state):
        x, y, tile_x, tile_y, area = state["coords"]
        coord_string = f"x:{tile_x} y:{tile_y} area:{area}"
        # Update seen_coords counter
        if coord_string in self.seen_coords:
            self.seen_coords[coord_string] += 1
        else:
            self.seen_coords[coord_string] = 1

    def update_explore_reward(self, state):
        explored_now = state["explored_locations"]
        explored_prev = self._prev_state.get("explored_locations", 0)
        explore_delta = explored_now - explored_prev
        return self.reward_scale * self.explore_weight * explore_delta  if explore_delta > 0 else 0

    def update_revisit_reward(self, state):
        x, y, tile_x, tile_y, area = state["coords"]
        coord_string = f"x:{tile_x} y:{tile_y} area:{area}"
        visit_count = self.seen_coords.get(coord_string, 0)
        revisit_penalty = self.revisit_weight if visit_count >= 5 else 0
        return self.reward_scale * revisit_penalty
            
    def update_area_discovery_reward(self, state):
        x, y, tile_x, tile_y, area = state["coords"]
        current_area = state["area"]
        area_discovery = 0
        if current_area not in self.discovered_areas and not current_area.startswith("Unknown Area"):
            if get_area_rewardable(x, y):
                self.discovered_areas.add(current_area)
                area_discovery = 1
                if current_area not in self.area_discovery_timestamps:
                    elapsed = time.time() - self._env_start_time
                    elapsed_td = timedelta(seconds=int(elapsed))
                    self.area_discovery_timestamps[current_area] = str(elapsed_td)
        return self.reward_scale * area_discovery * self.area_discovery_weight
    
    def update_rupee_reward(self, state):
        return self.reward_scale * (state["rupees"] - self._prev_state["rupees"]) * self.rupee_weight

    def update_health_reward(self, state):
        return self.reward_scale * (state["health"] - self._prev_state["health"]) * self.health_weight

    def update_death_reward(self):
        return self.reward_scale * self.died_count * -2.0

    def update_sword_reward(self, state):
        sword_now = state["sword"]
        sword_reward = 0
        if not self._sword_obtained and self._prev_sword == 0 and sword_now > 0:
            sword_reward = self.reward_scale * self.sword_weight
            self._sword_obtained = True
            # Record sword discovery timestamp
            if self.sword_discovery_timestamp is None:
                elapsed = time.time() - self._env_start_time
                elapsed_td = timedelta(seconds=int(elapsed))
                self.sword_discovery_timestamp = str(elapsed_td)
        return sword_reward

    def update_enemies_killed_reward(self, state):
        enemies_killed_delta = state["enemies_killed"] - self._prev_state["enemies_killed"]
        if enemies_killed_delta > 0:
            self.total_enemies_killed += enemies_killed_delta
        return self.reward_scale * enemies_killed_delta * self.enemies_killed_weight if enemies_killed_delta > 0 else 0

    def update_small_key_reward(self, state):
        small_keys_delta = state["small_keys"] - self._prev_state["small_keys"]
        if small_keys_delta > 0:
            self.total_small_keys += small_keys_delta
        return self.reward_scale * small_keys_delta * self.small_key_weight if small_keys_delta > 0 else 0

    
    def get_game_state_reward(self, state):

        # Explore reward
        explore_reward = self.update_explore_reward(state)
        # Area discovery reward
        area_discovery_reward = self.update_area_discovery_reward(state)
        # Revisit penalty
        revisit_reward = self.update_revisit_reward(state)

        # Rupee reward
        rupee_reward = self.update_rupee_reward(state)
        # Health reward
        health_reward = self.update_health_reward(state)
        # Death reward
        death_reward = self.update_death_reward()

        # Sword reward 
        sword_reward = self.update_sword_reward(state)
        # Enemies killed reward
        enemies_killed_reward = self.update_enemies_killed_reward(state)
        # Small key reward 
        small_key_reward = self.update_small_key_reward(state)

        # State scores
        state_scores = {
            "rupees": rupee_reward,
            "health": health_reward,
            "explore": explore_reward,
            "death": death_reward,
            "area_discovery": area_discovery_reward,
            "sword": sword_reward,
            "revisit": revisit_reward,
            "enemies_killed": enemies_killed_reward,
            "small_keys": small_key_reward,
        }
        return state_scores


    def reward(self, gba, observation):
        state = self.game_state(gba)
        # check if first interation
        if self._prev_state is None:
            self._prev_state = state
            # persist state data
            self.persist_state_data(state)
            # initialize last reward components
            self.last_reward_components = {k: 0.0 for k in [
                "rupees", "health", "explore", "death", "area_discovery", "sword", "revisit", "enemies_killed", "small_keys"
            ]}
            return 0.0

        # Detect new death (health drops to 0 from >0)
        if state["health"] == 0 and self._prev_state.get("health", 1) > 0:
            self.died_count += 1
            self.total_deaths += 1

        # Update seen coordinates before calculating rewards
        self.update_seen_coords(state)
        
        # Calculate rewards
        rewards = self.get_game_state_reward(state)
        total_reward = sum(rewards.values())

        # update last reward components
        self.last_reward_components = rewards.copy()  

        # persist state data
        self.persist_state_data(state)

        # update previous state
        self._prev_state = state

        # # return delta of a delta reward
        # prev_reward = self._prev_reward
        # self._prev_reward = total_reward
        # return total_reward - prev_reward
        
        # return delta reward
        return total_reward 

    def game_over(self, gba, observation):
        state = self.game_state(gba)
        return state["health"] == 0

    def reset(self, gba):
        self._prev_state = self.game_state(gba)
        self._prev_reward = 0.0
        self.seen_coords = {}
        self.discovered_areas = set()
        self.died_count = 0
        # persist state data
        self.persist_state_data(self._prev_state)

    def info(self, gba, observation):
        state = self.game_state(gba)
        state.update({
            "total_deaths": self.total_deaths,
            "is_dead": state["health"] == 0,
            "current_coords": state["coords"],
            "explored_locations": len(self.seen_coords),
            "discovered_areas": self.discovered_areas,
            "area_discovery_timestamps": self.area_discovery_timestamps,
            "sword_discovery_timestamp": self.sword_discovery_timestamp,
            "deaths": self.died_count,
            "total_enemies_killed": self.total_enemies_killed,
            "total_small_keys": self.total_small_keys,
            "reward_components": self.last_reward_components
        })
        return state 