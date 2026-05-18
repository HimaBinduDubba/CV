"""Engineering-rule validation for extracted data."""

from __future__ import annotations

from .models import Datum, Dimension, GDTCallout, Tolerance, ToleranceType, ValidationResult


class DataValidator:
    """Validates extracted data against engineering rules."""

    def validate_dimension(self, dimension: Dimension) -> ValidationResult:
        warnings: list[str] = []
        errors: list[str] = []

        if dimension.nominal_value <= 0:
            errors.append(f"Dimension {dimension.id} has non-positive nominal value")
        if not dimension.unit.strip():
            errors.append(f"Dimension {dimension.id} is missing a unit")
        if dimension.tolerance is None or dimension.tolerance.tolerance_type is ToleranceType.MISSING:
            warnings.append(f"Dimension {dimension.id} is missing explicit tolerance data")

        tolerance_result = (
            self.validate_tolerance(dimension.tolerance, dimension.nominal_value)
            if dimension.tolerance is not None
            else ValidationResult(is_valid=True, warnings=warnings, validation_score=0.85)
        )
        result = ValidationResult.combine(
            ValidationResult(is_valid=not errors, warnings=warnings, errors=errors, validation_score=0.5 if errors else 1.0),
            tolerance_result,
        )
        return self._with_warning_penalty(result)

    def validate_tolerance(self, tolerance: Tolerance, nominal: float) -> ValidationResult:
        warnings: list[str] = []
        errors: list[str] = []

        if tolerance.tolerance_type is ToleranceType.MISSING:
            warnings.append("Tolerance is missing")
            return ValidationResult(is_valid=True, warnings=warnings, validation_score=0.85)

        if tolerance.tolerance_type in (ToleranceType.BILATERAL, ToleranceType.UNILATERAL):
            if tolerance.plus is None and tolerance.minus is None:
                errors.append("Tolerance requires at least one plus/minus value")
            if tolerance.max_deviation(nominal) >= abs(nominal):
                errors.append("Tolerance magnitude must be smaller than nominal dimension")

        if tolerance.tolerance_type is ToleranceType.LIMIT:
            if tolerance.lower_limit is None or tolerance.upper_limit is None:
                errors.append("Limit tolerance requires lower_limit and upper_limit")
            elif tolerance.lower_limit >= tolerance.upper_limit:
                errors.append("Limit tolerance lower_limit must be less than upper_limit")
            elif not (tolerance.lower_limit <= nominal <= tolerance.upper_limit):
                warnings.append("Nominal value is outside tolerance limits")
            elif tolerance.max_deviation(nominal) >= abs(nominal):
                errors.append("Limit range is unreasonably large compared with nominal")

        score = 0.45 if errors else 1.0
        return self._with_warning_penalty(ValidationResult(is_valid=not errors, warnings=warnings, errors=errors, validation_score=score))

    def validate_datum_references(self, gdt_callouts: list[GDTCallout], datum_labels: list[str | Datum]) -> ValidationResult:
        defined = {
            (datum.label if isinstance(datum, Datum) else datum).upper()
            for datum in datum_labels
        }
        errors: list[str] = []
        for callout in gdt_callouts:
            for reference in callout.datum_references:
                if reference.upper() not in defined:
                    errors.append(f"GDT callout {callout.id} references undefined datum {reference}")
        return ValidationResult(is_valid=not errors, errors=errors, validation_score=0.4 if errors else 1.0)

    def validate_units(self, dimensions: list[Dimension]) -> ValidationResult:
        units = {dimension.unit for dimension in dimensions if dimension.unit}
        if len(units) <= 1:
            return ValidationResult.ok()
        return ValidationResult(
            is_valid=True,
            warnings=[f"Inconsistent units within part: {', '.join(sorted(units))}"],
            validation_score=0.75,
        )

    @staticmethod
    def _with_warning_penalty(result: ValidationResult) -> ValidationResult:
        if result.warnings and result.validation_score > 0.85:
            result.validation_score = 0.85
        return result
