"""Local Phase 6 wrapper: hold produce below its base market price."""

import main as candidate


candidate.SELL_MODE = "THRESHOLD"
candidate.MAX_NORMAL_SALE_BATCH = 0


def agent(obs):
    return candidate.agent(obs)
