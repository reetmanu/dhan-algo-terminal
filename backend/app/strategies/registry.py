from app.strategies.ema_crossover import EMACrossoverStrategy

STRATEGY_REGISTRY = {
    "ema_crossover": EMACrossoverStrategy,
}


def get_strategy_class(name: str):
    """Get strategy class by name"""
    return STRATEGY_REGISTRY.get(name)


def list_strategies():
    """List all available strategies with metadata"""
    result = []
    for name, cls in STRATEGY_REGISTRY.items():
        result.append({
            "name": name,
            "description": getattr(cls, 'description', ''),
            "default_params": getattr(cls, 'default_params', {})
        })
    return result
