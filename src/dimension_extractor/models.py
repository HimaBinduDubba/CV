"""Core data models for extracted engineering drawing data."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ToleranceType(Enum):
    BILATERAL = "bilateral"
    UNILATERAL = "unilateral"
    LIMIT = "limit"
    MISSING = "missing"


class GDTSymbol(Enum):
    FLATNESS = "flatness"
    STRAIGHTNESS = "straightness"
    CIRCULARITY = "circularity"
    CYLINDRICITY = "cylindricity"
    PROFILE_OF_LINE = "profile_of_line"
    PROFILE_OF_SURFACE = "profile_of_surface"
    ANGULARITY = "angularity"
    PERPENDICULARITY = "perpendicularity"
    PARALLELISM = "parallelism"
    POSITION = "position"
    CONCENTRICITY = "concentricity"
    SYMMETRY = "symmetry"
    CIRCULAR_RUNOUT = "circular_runout"
    TOTAL_RUNOUT = "total_runout"


class MaterialCondition(Enum):
    MMC = "maximum_material_condition"
    LMC = "least_material_condition"
    RFS = "regardless_of_feature_size"


class RelationshipType(Enum):
    BOLTED = "bolted"
    PRESSED = "pressed"
    WELDED = "welded"
    ADHESIVE = "adhesive"
    CONTACT = "contact"
    THREADED = "threaded"
    CLEARANCE = "clearance"


@dataclass(slots=True)
class Tolerance:
    tolerance_type: ToleranceType
    plus: float | None = None
    minus: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str | None = None
    confidence_score: float = 1.0

    def max_deviation(self, nominal: float | None = None) -> float:
        if self.tolerance_type is ToleranceType.MISSING:
            return 0.0
        if self.tolerance_type is ToleranceType.LIMIT:
            if self.lower_limit is None or self.upper_limit is None:
                return 0.0
            if nominal is None:
                return abs(self.upper_limit - self.lower_limit)
            return max(abs(self.upper_limit - nominal), abs(nominal - self.lower_limit))
        return max(abs(self.plus or 0.0), abs(self.minus or 0.0))


@dataclass(slots=True)
class Dimension:
    id: str
    nominal_value: float
    unit: str
    measured_feature: str
    part_id: str
    tolerance: Tolerance | None = None
    source_page: int | None = None
    source_zone: str | None = None
    drawing_number: str | None = None
    datum_references: list[str] = field(default_factory=list)
    confidence_score: float = 1.0
    requires_human_review: bool = False
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GDTCallout:
    id: str
    symbol_type: GDTSymbol
    tolerance_zone: float
    material_condition: MaterialCondition | None
    datum_references: list[str]
    controlled_feature: str
    part_id: str
    confidence_score: float = 1.0


@dataclass(slots=True)
class Datum:
    id: str
    label: str
    feature_description: str
    part_id: str
    confidence_score: float = 1.0


@dataclass(slots=True)
class MaterialSpec:
    material_type: str
    material_grade: str | None
    surface_finish: str | None
    heat_treatment: str | None
    part_id: str
    confidence_score: float = 1.0


@dataclass(slots=True)
class AssemblyRelationship:
    part1_id: str
    part2_id: str
    mating_surface1: str
    mating_surface2: str
    relationship_type: RelationshipType
    confidence_score: float = 1.0


@dataclass(slots=True)
class ChainLink:
    dimension_id: str
    contribution_sign: int
    contribution_rank: float

    def __post_init__(self) -> None:
        if self.contribution_sign not in (-1, 1):
            raise ValueError("contribution_sign must be +1 or -1")


@dataclass(slots=True)
class DimensionalChain:
    chain_id: str
    target_measurement: str
    contributing_dimensions: list[ChainLink]
    total_nominal: float
    worst_case_max: float
    worst_case_min: float
    confidence_score: float = 1.0


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    validation_score: float = 1.0

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(is_valid=True)

    @classmethod
    def combine(cls, *results: "ValidationResult") -> "ValidationResult":
        warnings: list[str] = []
        errors: list[str] = []
        score = 1.0
        for result in results:
            warnings.extend(result.warnings)
            errors.extend(result.errors)
            score = min(score, result.validation_score)
        return cls(is_valid=not errors, warnings=warnings, errors=errors, validation_score=score)


@dataclass(slots=True)
class ExtractionResult:
    source_file: Path
    part_id: str
    dimensions: list[Dimension] = field(default_factory=list)
    gdt_callouts: list[GDTCallout] = field(default_factory=list)
    datums: list[Datum] = field(default_factory=list)
    material_specs: list[MaterialSpec] = field(default_factory=list)
    validation: ValidationResult = field(default_factory=ValidationResult.ok)
    confidence_score: float = 0.0
    raw_responses: list[str] = field(default_factory=list)
    requires_human_review: bool = False


@dataclass(slots=True)
class AssemblyResult:
    source_file: Path
    part_ids: list[str] = field(default_factory=list)
    relationships: list[AssemblyRelationship] = field(default_factory=list)
    drawing_links: dict[str, str] = field(default_factory=dict)
    confidence_score: float = 0.0
    raw_response: str | None = None


@dataclass(slots=True)
class BatchResult:
    total_files: int
    successful: list[ExtractionResult | AssemblyResult] = field(default_factory=list)
    failed: dict[Path, str] = field(default_factory=dict)

    @property
    def processed_files(self) -> int:
        return len(self.successful) + len(self.failed)

    @property
    def progress_percent(self) -> float:
        if self.total_files == 0:
            return 100.0
        return (self.processed_files / self.total_files) * 100.0

