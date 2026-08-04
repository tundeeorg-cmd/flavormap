from src.config import RANDOM_SEED


def test_random_seed_pinned() -> None:
    assert RANDOM_SEED == 42
