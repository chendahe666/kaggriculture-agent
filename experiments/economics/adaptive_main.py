"""Local Phase 6 wrapper: choose wheat or carrot from live economics."""

import main as candidate


candidate.CROP_MODE = "ADAPTIVE"
candidate.SELL_MODE = "IMMEDIATE"


def agent(obs):
    return candidate.agent(obs)
