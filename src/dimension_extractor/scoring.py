"""Confidence scoring for extracted engineering data."""

from __future__ import annotations

from statistics import mean

from .models import Dimension, ExtractionResult, ValidationResult


class ConfidenceScorer:
    """Calculates confidence scores for extracted data."""

    review_threshold = 0.7

    def score_dimension(
        self,
        dimension: Dimension,
        llm_confidence: float,
        validation: ValidationResult,
    ) -> float:
        score = self._combine_scores(llm_confidence, validation.validation_score)
        if validation.errors:
            score *= 0.5
        elif validation.warnings:
            score *= 0.85
        score = self._clamp(score)
        dimension.confidence_score = score
        dimension.requires_human_review = score < self.review_threshold
        return score

    def score_extraction_result(self, result: ExtractionResult) -> float:
        scores = [dimension.confidence_score for dimension in result.dimensions]
        scores.extend(callout.confidence_score for callout in result.gdt_callouts)
        scores.extend(datum.confidence_score for datum in result.datums)
        scores.extend(spec.confidence_score for spec in result.material_specs)

        if scores:
            overall = self._combine_scores(mean(scores), result.validation.validation_score)
        else:
            overall = self._combine_scores(0.0, result.validation.validation_score)

        result.confidence_score = overall
        result.requires_human_review = overall < self.review_threshold or any(
            dimension.requires_human_review for dimension in result.dimensions
        )
        return overall

    def _combine_scores(self, llm_confidence: float, validation_score: float) -> float:
        return self._clamp((0.7 * self._clamp(llm_confidence)) + (0.3 * self._clamp(validation_score)))

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

