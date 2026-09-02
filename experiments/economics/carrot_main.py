"""Local Phase 6 wrapper: pure carrot control."""

import main as candidate


candidate.CROP_MODE = "CARROT"
candidate.SELL_MODE = "IMMEDIATE"


def agent(obs):
    return candidate.agent(obs)
