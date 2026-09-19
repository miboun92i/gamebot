RANKS = [
    ("Bronze I", 0), ("Bronze II", 750), ("Bronze III", 1500),
    ("Silver I", 2500), ("Silver II", 3500), ("Silver III", 4500),
    ("Gold I", 6000), ("Gold II", 7500), ("Gold III", 9000),
    ("Platinum I", 11000), ("Platinum II", 13000), ("Platinum III", 15000),
    ("Diamond I", 17500), ("Diamond II", 20000), ("Diamond III", 22500),
    ("Immortal I", 24500), ("Immortal II", 26500), ("Immortal III", 28500),
    ("Radiant", 30000),
]

def rank_for_xp(xp: int) -> str:
    current = RANKS[0][0]
    for name, threshold in RANKS:
        if xp < threshold:
            break
        current = name
    return current

def next_rank(xp: int):
    for name, threshold in RANKS:
        if threshold > xp:
            return name, threshold
    return None, None
