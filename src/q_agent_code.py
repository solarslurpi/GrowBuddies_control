import numpy as np

from heatmap_animator_code import HeatmapAnimator
from q_datahandler_code import QDataHandler


class QLearningAgent:
    def __init__(self, logger, learning_rate=0.1, discount_rate=0.99, exploration_rate=1.0, exploration_decay=0.995, min_exploration_rate=0.01):
        self.logger = logger
        # Set the state space size based on the number of bins for discretizing the error
        self.state_space_size = 10  # 10 bins for the discretized error

        # Set the action space size based on the number of discrete actions you have
        self.action_space_size = 21  # Actions from -10 to 10, inclusive


        self.learning_rate = learning_rate
        self.discount_rate = discount_rate
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.min_exploration_rate = min_exploration_rate

        # Initialize the Q-table with zeros
        self.q_table = np.zeros((self.state_space_size, self.action_space_size))
        # start the heatmap.
        self.qdata = QDataHandler()
        heatmap = HeatmapAnimator(num_states= self.state_space_size, num_actions=self.action_space_size)
        heatmap.start_animation()
    def decide_action(self, state):
        """Decide an action based on the current state using the epsilon-greedy policy.

        Args:
            state (int): The current state of the environment, represented by the index of the discretized error bin.

        Returns:
            int: The index of the action to take.
        """
        # Exploration-exploitation decision
        if np.random.rand() < self.exploration_rate:
            # Exploration: choose a random action
            action = np.random.randint(0, self.action_space_size)
        else:
            # Exploitation: choose the action with the highest Q-value for the current state
            action = np.argmax(self.q_table[state])
        self.logger.debug(f"Decided Action: {action}")
        return action

    def update_policy(self, state, action, reward, next_state, done):
        """Update the Q-table using the Q-learning formula.

        Args:
            state (int): The current state (index of the discretized error bin).
            action (int): The action taken.
            reward (float): The reward received for taking the action.
            next_state (int): The next state as a result of the action.
            done (bool): Indicates if the episode has ended.
        """
        # Predict the future reward from the next state
        future_rewards = np.max(self.q_table[next_state])

        # Update the Q-value for the current state-action pair
        old_value = self.q_table[state, action]
        new_value = old_value + self.learning_rate * (reward + self.discount_rate * future_rewards - old_value)

        self.q_table[state, action] = new_value
        self.qdata.put_q_data((state, action, new_value))
        # Update the exploration rate if the episode is not done
        if not done:
            self.exploration_rate = max(self.min_exploration_rate, self.exploration_rate * self.exploration_decay)
