""" Task wrapper for NLE that can change tasks at reset using the NLE's task definition format. """
import copy
import time
from typing import List, Callable
import numpy as np
import gymnasium as gym
from gym import spaces

from syllabus.core import TaskWrapper

class ReinitTaskWrapper(TaskWrapper):
    """
    This is a general wrapper for tasks defined as subclasses of a base environment.

    This wrapper reinitializes the environment with the provided env function at the start of each episode.
    This is a simple, general solution to using Syllabus with tasks that need to be reinitialized, but it is inefficient.
    It's likely that you can achieve better performance by using a more specialized wrapper.
    """
    def __init__(self, env: gym.Env, env_fn: Callable, task_space: gym.Space = None):
        super().__init__(env)

        self.env_fn = env_fn
        self.task_envs = {}     # Save instance of each task environment to avoid reinitializing
        self.task_space = task_space

        # Tracking episode end
        self.done = True

    def reset(self, new_task: int = None, **kwargs):
        """
        Resets the environment along with all available tasks, and change the current task.
        """
        # Change task if new one is provided
        if new_task is not None:
            self.change_task(new_task)

        self.done = False

        return self.observation(self.env.reset(**kwargs))

    def change_task(self, new_task: int):
        """
        Change task by directly editing environment class.

        This ensures that all instance variables are reset, not just the ones for the current task.
        We do this efficiently by keeping track of which reset functions have already been called,
        since very few tasks override reset. If new_task is provided, we change the task before
        calling the final reset.
        """
        # Ignore new task if mid episode
        if not self.done:
            raise RuntimeError("Cannot change task mid-episode.")

        # Update current task
        if new_task not in self.task_envs:
            self.task_envs[new_task] = self.env_fn(new_task)
        
        self.env = self.task_envs[new_task]

    def step(self, action):
        """
        Step through environment and update task completion.
        """
        obs, rew, done, info = self.env.step(action)
        self.done = done
        info["task_completion"] = self._task_completion(obs, rew, done, info)
        return self.observation(obs), rew, done, info


if __name__ == "__main__":
    from nle.env import base
    from nle.env.tasks import (NetHackScore,
                           NetHackStaircase,
                           NetHackStaircasePet,
                           NetHackOracle,
                           NetHackGold,
                           NetHackEat,
                           NetHackScout)

    def run_episode(env, task: str = None, verbose=1):
        env.reset(new_task=task)
        task_name = type(env.unwrapped).__name__
        done = False
        ep_rew = 0
        while not done:
            action = env.action_space.sample()
            _, rew, done, _ = env.step(action)
            ep_rew += rew
        if verbose:
            print(f"Episodic reward for {task_name}: {ep_rew}")

    print("Testing NethackTaskWrapper")
    N_EPISODES = 100

    # Initialize NLE
    def create_env(task):
        task_class = [NetHackScore, NetHackStaircase, NetHackStaircasePet, NetHackOracle, NetHackGold, NetHackEat, NetHackScout][task]
        return task_class()

    nethack_env = NetHackScore()    
    nethack_task_env = ReinitTaskWrapper(nethack_env, create_env)

    start_time = time.time()

    for _ in range(N_EPISODES):
        run_episode(nethack_task_env, verbose=0)

    end_time = time.time()
    print(f"Run time same task: {end_time - start_time}")
    start_time = time.time()

    for _ in range(N_EPISODES):
        nethack_task = gym.spaces.Discrete(7).sample()
        run_episode(nethack_task_env, task=nethack_task, verbose=0)

    end_time = time.time()
    print(f"Run time swapping tasks: {end_time - start_time}")