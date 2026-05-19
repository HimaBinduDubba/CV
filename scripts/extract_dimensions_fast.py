from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.api.router import APIRouter
from src.config import APIConfig
from src.dimension_extractor.extractor import DimensionExtractor
from src.dimension_extractor.models import ExtractionResult, ValidationResult
from src.dimension_extractor.pdf_converter import PDFConverter


class DataclassEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


def parse_page(extractor: DimensionExtractor, raw_text: str) -> dict[str, Any]:
    return {
        "dimensions": extractor._parse_dimension_response(raw_text),
        "gdt_callouts": extractor._parse_gdt_response(raw_text),
        "datums": extractor._parse_datum_response(raw_text),
        "material_specs": extractor._parse_material_response(raw_text),
    }


def process_page(
    page_index: int,
    image: Any,
    prompt: str,
    config_file: Path,
) -> tuple[int, dict[str, Any], str, dict[str, Any]]:
    config = APIConfig.from_file(config_file)
    router = APIRouter(config)
    extractor = DimensionExtractor(api_router=router, pdf_converter=None)
    response = router.extract_from_image(prompt, [image])
    raw_text = extractor._response_text(response)
    parsed = parse_page(extractor, raw_text)
    return page_index, parsed, raw_text, router.get_usage_stats()


def process_pdf(
    pdf_path: Path,
    config_file: Path,
    dpi: int,
    workers: int,
    output_path: Path,
    state: dict[str, Any],
) -> ExtractionResult:
    converter = PDFConverter(dpi=dpi)
    base_config = APIConfig.from_file(config_file)
    base_router = APIRouter(base_config)
    extractor = DimensionExtractor(api_router=base_router, pdf_converter=converter)
    pages = converter.convert(pdf_path)
    prompt = extractor._build_dimension_prompt(pdf_path.name)

    dimensions = []
    gdt_callouts = []
    datums = []
    material_specs = []
    raw_responses = []
    page_errors: dict[str, str] = {}
    base_usage = state.get("usage", {})
    usage = {"total_requests": 0, "total_tokens": 0, "total_estimated_cost": 0.0}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_page, index, image, prompt, config_file): index
            for index, image in enumerate(pages, start=1)
        }
        for future in as_completed(futures):
            page_number = futures[future]
            try:
                _, parsed, raw_text, page_usage = future.result()
                for dimension in parsed["dimensions"]:
                    dimension.source_page = page_number
                dimensions.extend(parsed["dimensions"])
                gdt_callouts.extend(parsed["gdt_callouts"])
                datums.extend(parsed["datums"])
                material_specs.extend(parsed["material_specs"])
                raw_responses.append(raw_text)
                usage["total_requests"] += page_usage["total_requests"]
                usage["total_tokens"] += page_usage["total_tokens"]
                usage["total_estimated_cost"] += page_usage["total_estimated_cost"]
            except Exception as exc:
                page_errors[str(page_number)] = f"{type(exc).__name__}: {exc}"

            state["usage"] = add_usage(base_usage, usage)
            output_path.write_text(json.dumps(state, cls=DataclassEncoder, indent=2), encoding="utf-8")

    part_id = extractor._infer_part_id(pdf_path, dimensions, material_specs)
    validation = extractor._validate_part(dimensions, gdt_callouts, datums)
    for dimension in dimensions:
        dimension_validation = extractor.validator.validate_dimension(dimension)
        extractor.confidence_scorer.score_dimension(dimension, dimension.confidence_score, dimension_validation)

    result = ExtractionResult(
        source_file=pdf_path,
        part_id=part_id,
        dimensions=dimensions,
        gdt_callouts=gdt_callouts,
        datums=datums,
        material_specs=material_specs,
        validation=validation,
        raw_responses=raw_responses,
    )
    extractor.confidence_scorer.score_extraction_result(result)
    if page_errors:
        state.setdefault("page_errors", {})[str(pdf_path)] = page_errors
    state["usage"] = add_usage(base_usage, usage)
    return result


def process_assembly(png_path: Path, config_file: Path) -> Any:
    config = APIConfig.from_file(config_file)
    router = APIRouter(config)
    extractor = DimensionExtractor(api_router=router, pdf_converter=None)
    return extractor.process_assembly_diagram(png_path), router.get_usage_stats()


def add_usage(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_requests": int(left.get("total_requests", 0)) + int(right.get("total_requests", 0)),
        "total_tokens": int(left.get("total_tokens", 0)) + int(right.get("total_tokens", 0)),
        "total_estimated_cost": float(left.get("total_estimated_cost", 0.0)) + float(right.get("total_estimated_cost", 0.0)),
    }


def write_dimension_csv(state: dict[str, Any], csv_path: Path) -> None:
    rows = []
    for part in state.get("parts", []):
        for dimension in part.get("dimensions", []):
            tolerance = dimension.get("tolerance") or {}
            rows.append(
                {
                    "source_file": part.get("source_file"),
                    "part_id": dimension.get("part_id") or part.get("part_id"),
                    "dimension_id": dimension.get("id"),
                    "nominal_value": dimension.get("nominal_value"),
                    "unit": dimension.get("unit"),
                    "measured_feature": dimension.get("measured_feature"),
                    "tolerance_type": tolerance.get("tolerance_type"),
                    "plus": tolerance.get("plus"),
                    "minus": tolerance.get("minus"),
                    "lower_limit": tolerance.get("lower_limit"),
                    "upper_limit": tolerance.get("upper_limit"),
                    "confidence_score": dimension.get("confidence_score"),
                    "source_page": dimension.get("source_page"),
                    "requires_human_review": dimension.get("requires_human_review"),
                }
            )
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else ["source_file"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast resumable Gemini dimension extraction.")
    parser.add_argument("--data-dir", type=Path, default=Path("Data"))
    parser.add_argument("--config", type=Path, default=Path("config.local.json"))
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("results/full_extraction/extraction_results_gemini.json"))
    args = parser.parse_args()

    start = time.time()
    config = APIConfig.from_file(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {
        "metadata": {
            "api_provider": config.provider,
            "gemini_model": config.gemini_model,
            "dpi": args.dpi,
            "workers": args.workers,
        },
        "parts": [],
        "assembly": None,
        "dimensional_chains": [],
        "errors": {},
        "page_errors": {},
        "usage": {},
    }

    pdfs = sorted(args.data_dir.glob("*.pdf"))
    for pdf_path in pdfs:
        print(f"PROCESS {pdf_path.name}", flush=True)
        try:
            result = process_pdf(pdf_path, args.config, args.dpi, args.workers, args.output, state)
            state["parts"].append(result)
            print(
                f"OK {pdf_path.name}: dimensions={len(result.dimensions)} "
                f"gdt={len(result.gdt_callouts)} datums={len(result.datums)} "
                f"materials={len(result.material_specs)} confidence={result.confidence_score:.3f}",
                flush=True,
            )
        except Exception as exc:
            state["errors"][str(pdf_path)] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR {pdf_path.name}: {type(exc).__name__}: {exc}", flush=True)
        args.output.write_text(json.dumps(state, cls=DataclassEncoder, indent=2), encoding="utf-8")

    assembly_path = args.data_dir / "Assemble_Diagram.png"
    if assembly_path.exists():
        print(f"PROCESS {assembly_path.name}", flush=True)
        try:
            assembly, usage = process_assembly(assembly_path, args.config)
            state["assembly"] = assembly
            state["usage"] = add_usage(state.get("usage", {}), usage)
            print(
                f"OK {assembly_path.name}: parts={len(assembly.part_ids)} "
                f"relationships={len(assembly.relationships)} confidence={assembly.confidence_score:.3f}",
                flush=True,
            )
        except Exception as exc:
            state["errors"][str(assembly_path)] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR {assembly_path.name}: {type(exc).__name__}: {exc}", flush=True)

    if state["parts"] and state["assembly"]:
        extractor = DimensionExtractor()
        try:
            state["dimensional_chains"] = extractor.identify_dimensional_chains(state["parts"], state["assembly"])
        except Exception as exc:
            state["errors"]["dimensional_chains"] = f"{type(exc).__name__}: {exc}"

    state["metadata"]["elapsed_seconds"] = round(time.time() - start, 2)
    args.output.write_text(json.dumps(state, cls=DataclassEncoder, indent=2), encoding="utf-8")
    write_dimension_csv(json.loads(args.output.read_text(encoding="utf-8")), args.output.with_suffix(".csv"))
    print(f"WROTE {args.output}", flush=True)
    print(f"WROTE {args.output.with_suffix('.csv')}", flush=True)


if __name__ == "__main__":
    main()
