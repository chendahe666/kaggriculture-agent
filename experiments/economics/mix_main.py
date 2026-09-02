"""Local Phase 6 wrapper: fixed three-wheat/three-carrot crop mix."""

import main as candidate


candidate.CROP_MODE = "MIX"
candidate.SELL_MODE = "IMMEDIATE"


def agent(obs):
    return candidate.agent(obs)
