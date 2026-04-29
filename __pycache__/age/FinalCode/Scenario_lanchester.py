def lanchester_scenario(engine, unit_type, N):
    """Validation scientifique (Section 69.3)."""
    stats = {
        "Crossbowman": {"hp": 35, "attack": 5, "reload_time": 2.0, "range": 5.0, "speed": 0.96, "tags": ["archer"]},
        "knight": {"hp": 100, "attack": 10, "reload_time": 1.8, "armor": 2, "range": 1.0, "speed": 1.35, "tags": ["Cavalry"]},
    }
    u_stats = stats.get(unit_type, stats["knight"])
    # Engagement immÃ©diat
    x_p1, x_p2 = 20.0, 21.2 

    for i in range(N):
        engine.spawn_unit(player=1, x=x_p1 - (i%5)*0.6, y=30 + (i//5)*0.6, unit_type=unit_type, **u_stats)
    for i in range(2 * N):
        engine.spawn_unit(player=2, x=x_p2 + (i%5)*0.6, y=30 + (i//5)*0.6, unit_type=unit_type, **u_stats)
