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
