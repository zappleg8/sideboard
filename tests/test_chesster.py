from sideboard.chesster import get_quip, GameEvent, QUIPS


def test_all_events_have_quips():
    for event in GameEvent:
        assert len(QUIPS[event]) >= 3, f"{event.value} has < 3 quips"


def test_get_quip_returns_string():
    quip = get_quip(GameEvent.GAME_START)
    assert isinstance(quip, str)
    assert len(quip) > 0


def test_get_quip_with_context():
    quip = get_quip(GameEvent.OPENING_RECOGNIZED, name="Sicilian Defense")
    assert isinstance(quip, str)


def test_get_quip_no_immediate_repeat():
    quips = set()
    for _ in range(20):
        quips.add(get_quip(GameEvent.GAME_START))
    assert len(quips) >= 2


def test_total_quip_count():
    total = sum(len(v) for v in QUIPS.values())
    assert total >= 70, f"Only {total} quips — need at least 70"


def test_template_substitution_with_missing_key():
    quip = get_quip(GameEvent.CHESSTER_WINS, move_number=42)
    assert isinstance(quip, str)
