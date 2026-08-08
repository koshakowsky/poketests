from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Internal Use

class HealthResponse(StrictModel):
    status: str
    service: str


# Pokemon: list & detail

class TypeRef(StrictModel):
    id: int
    name: str


class PokemonListItem(StrictModel):
    id: int
    name: str
    sprite_url: Optional[str]
    types: list[TypeRef]
    stat_total: int
    generation: Optional[int]
    is_legendary: bool
    is_mythical: bool
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


class PaginatedResponse(StrictModel):
    items: list[PokemonListItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class AbilityRef(StrictModel):
    id: int
    name: str
    short_effect: Optional[str]


class EggGroupRef(StrictModel):
    id: int
    name: str


class PokemonDetail(StrictModel):
    id: int
    name: str
    height: Optional[int]
    weight: Optional[int]
    base_experience: Optional[int]
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    stat_total: int
    sprite_url: Optional[str]
    sprite_official: Optional[str]
    generation: Optional[int]
    is_legendary: bool
    is_mythical: bool
    is_baby: bool
    habitat: Optional[str]
    color: Optional[str]
    shape: Optional[str]
    growth_rate: Optional[str]
    capture_rate: Optional[int]
    base_happiness: Optional[int]
    gender_rate: Optional[int]
    types: list[TypeRef]
    abilities: list[AbilityRef]
    egg_groups: list[EggGroupRef]
    height_m: Optional[float]
    weight_kg: Optional[float]


# Similar

class SimilarEntry(StrictModel):
    pokemon: PokemonListItem
    similarity_score: float
    matching_types: list[str]
    stat_difference: float


# Compare

class StatComparisonEntry(StrictModel):
    values: dict[str, int]
    max: int
    min: int
    leader: list[str]
    spread: int


class TypeAdvantageDetail(StrictModel):
    attack_type: str
    defend_type: str
    multiplier: float


class TypeAdvantage(StrictModel):
    best_multiplier: float
    details: list[TypeAdvantageDetail]
    verdict: Literal["super_effective", "not_effective", "neutral"]


class StatDuel(StrictModel):
    difference: int
    winner: str


class StatAdvantage(StrictModel):
    stats_won: int
    stats_lost: int
    stats_tied: int
    details: dict[str, StatDuel]


class AdvantageEntry(StrictModel):
    type_advantage: TypeAdvantage
    stat_advantage: StatAdvantage


class CompareResponse(StrictModel):
    pokemon: list[PokemonDetail]
    stat_comparison: dict[str, StatComparisonEntry]
    advantages: dict[str, dict[str, AdvantageEntry]]


# Analytics

class CategoryStat(StrictModel):
    category: str
    count: int
    avg_stat_total: float
    avg_hp: float
    avg_attack: float
    avg_defense: float
    avg_sp_attack: float
    avg_sp_defense: float
    avg_speed: float
    min_stat_total: int
    max_stat_total: int


class TypeDistribution(StrictModel):
    type_name: str
    count: int
    percentage: float
    avg_stat_total: float


class GenerationStats(StrictModel):
    generation: int
    total_pokemon: int
    avg_stat_total: float
    legendary_count: int
    mythical_count: int
    type_distribution: list[TypeDistribution]


# Types / effectiveness

class EffectivenessRow(StrictModel):
    type: str
    multiplier: float


class EffectivenessResponse(StrictModel):
    attacking: list[EffectivenessRow]
    defending: list[EffectivenessRow]


# Auth — `extra="forbid"` is the structural security oracle: a leaked
# `hashed_password`/`password` field fails these (TC-AUTH-15).

class UserOut(StrictModel):
    id: int
    email: str
    tier: str


class TokenResponse(StrictModel):
    access_token: str
    token_type: str


# Billing — likewise forbids a full `card_number`/`cvc` ever appearing
# (TC-BILL-17). `current_period_end` arrives as an ISO datetime string.

class PlanOut(StrictModel):
    id: str
    name: str
    price_cents: int
    currency: str
    interval: str


class SubscriptionOut(StrictModel):
    status: str
    plan: Optional[str]
    card_brand: Optional[str]
    card_last4: Optional[str]
    current_period_end: Optional[str]
