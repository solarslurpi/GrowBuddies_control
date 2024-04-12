import itertools

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.animation import FuncAnimation

from q_datahandler_code import QDataHandler

class HeatmapAnimator:
    def __init__(self, num_states, num_actions):
        self.num_states = num_states
        self.num_actions = num_actions
        self.grid = np.zeros((num_states, num_actions))

        # Custom colormap with shades of green for better text visibility
        self.cmap_green = LinearSegmentedColormap.from_list("shades_of_green", ["black", "green"])

        # Set up the figure and axis
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.im = self.ax.imshow(self.grid, cmap=self.cmap_green, vmin=0, vmax=1, aspect='equal')

        # Colorbar setup
        self.cbar = self.fig.colorbar(self.im, ax=self.ax, orientation='vertical', label='Q-Value')
        self.cbar.set_ticks(np.linspace(0, 1, 11))

        # Adjust tick marks and labels
        self.ax.set_xticks(np.arange(0.5, num_actions + 0.5, 1))
        self.ax.set_yticks(np.arange(0.5, num_states + 0.5, 1))
        self.ax.set_xticklabels(np.arange(num_actions))
        self.ax.set_yticklabels(np.arange(num_states))

        self.ani = None
        self.qdata = QDataHandler()

    def fetch_qvalue(self):
        # Placeholder for actual logic to fetch or simulate Q-values
        # Replace with the actual data retrieval logic.
        data = self.qdata.get_q_data()
        print(f"fetch_qvalue.  Data: {data}")
        return data


    def update(self, frame):
        qvalue_data = self.fetch_qvalue()
        if qvalue_data:
            x, y, value = qvalue_data
            self.grid[x, y] = value

        self.ax.clear()
        self.ax.imshow(self.grid, cmap=self.cmap_green, vmin=0, vmax=1, aspect='equal', origin='lower', extent=[0, self.num_actions, 0, self.num_states])
        self.ax.set_xticks(np.arange(0.5, self.num_actions + 0.5, 1))
        self.ax.set_yticks(np.arange(0.5, self.num_states + 0.5, 1))
        self.ax.set_xticklabels(np.arange(self.num_actions))
        self.ax.set_yticklabels(np.arange(self.num_states))

        for i in range(self.num_states):
            for j in range(self.num_actions):
                if self.grid[i, j] > 0:
                    self.ax.text(j + 0.5, i + 0.5, f"{self.grid[i, j]:.2f}", ha="center", va="center", color="white")

        plt.title(f"Update #{frame}")

    def start_animation(self):
        # Use the `cache_frame_data=False` option to prevent caching issues with indefinite frames
        self.ani = FuncAnimation(self.fig, self.update, frames=itertools.count(), repeat=False, cache_frame_data=False)
        plt.show()

# To use the class:
animator = HeatmapAnimator(num_states=10, num_actions=10)
animator.start_animation()
