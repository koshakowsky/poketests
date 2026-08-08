from dataclasses import dataclass


@dataclass(frozen=True)
class PokemonAnchor:
    id: int
    name: str
    stat_total: int | None = None
    types: frozenset = frozenset()


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    sut_fixture: str
    total: int
    max_id: int
    generations: tuple
    legendary_count: int
    mythical_count: int
    stat_total_max: int
    hp_max: int
    # Anchors
    bulbasaur: PokemonAnchor
    charmander: PokemonAnchor
    mewtwo: PokemonAnchor
    mew: PokemonAnchor


GEN1 = DatasetProfile(
    name="gen1",
    sut_fixture="api/fixtures/gen1.json",
    total=151,
    max_id=151,
    generations=(1,),
    legendary_count=4,      # articuno, zapdos, moltres, mewtwo
    mythical_count=1,       # mew — mythical, but not legendary
    stat_total_max=680,     # mewtwo
    hp_max=250,             # chansey (id=113)
    bulbasaur=PokemonAnchor(1, "bulbasaur", 318, frozenset({"grass", "poison"})),
    charmander=PokemonAnchor(4, "charmander"),
    mewtwo=PokemonAnchor(150, "mewtwo", 680),
    mew=PokemonAnchor(151, "mew"),
)

PROFILE = GEN1


@dataclass(frozen=True)
class TestCards:
    """Fake-gateway test card numbers — see test-cases/api/11-billing-checkout.md.
    All are Luhn-valid; the outcome is the gateway's business decision."""
    visa_ok: str = "4242424242424242"
    amex_ok: str = "378282246310005"       # amex → CVC is 4 digits
    declined: str = "4000000000000002"     # → 402 card_declined
    insufficient: str = "4000000000009995" # → 402 insufficient_funds
    luhn_invalid: str = "4242424242424241" # last digit flipped → invalid_number


CARDS = TestCards()
