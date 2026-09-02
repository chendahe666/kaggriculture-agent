"""Local Phase 6/7 wrapper for the rejected V5 adaptive candidate."""

import main as candidate


candidate.CROP_MODE = "ADAPTIVE"
candidate.SELL_MODE = "THRESHOLD"
candidate.MAX_NORMAL_SALE_BATCH = 0
candidate.LAST_CYCLE_TILE_COUNT = 5


def agent(obs):
    return candidate.agent(obs)
