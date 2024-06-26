import matplotlib.pyplot as plt
import numpy as np

def custom_decay(n_games, max_games, k=1, midpoint=0.1):
    # The logistic function for S-curve
    return 1 / (1 + np.exp(-k * ((n_games / max_games) - midpoint)))

# Values for n_games
max_games = 82 # use 64 for goalies
n_games = np.linspace(0, max_games, 100)  # More points for a smoother curve

# Plot the decay for different values of k
plt.figure(figsize=(10, 6))
for k in [5, 10, 15, 20]:
    plt.plot(n_games, custom_decay(n_games, max_games, k), label=f'k={k}')

plt.title('Effect of Different k Values on Decay Function')
plt.xlabel('Number of Games (n_games)')
plt.ylabel('Decay Value')
plt.legend()
plt.grid(True)
plt.show()
