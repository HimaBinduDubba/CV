# Results

Generated extraction outputs are organized here. Original source PDFs, PNG, PPTX, and docs remain in `Data/`.

## Folder Layout

- `full_extraction/` - complete Gemini extraction across all drawings.
- `stackup/` - focused dimensions relevant to bolt protrusion tolerance stack-up analysis.
- `references/ppt_media/` - extracted PowerPoint images used to identify the stack-up callouts.

## Full Extraction Summary

| Source file | Dimensions | GD&T | Datums | Materials | Confidence |
|---|---:|---:|---:|---:|---:|
| 5377630-01-Front_case.pdf | 270 | 18 | 30 | 3 | 0.694 |
| 5377631-01-Rare_case.pdf | 479 | 3 | 36 | 6 | 0.705 |
| 5377632-R10AS.pdf | 203 | 13 | 12 | 13 | 0.693 |
| AS2159-Washer.pdf | 49 | 3 | 1 | 1 | 0.695 |
| AS3580-Bolt.pdf | 1561 | 1 | 6 | 6 | 0.676 |
| ST2780-Nut.pdf | 72 | 1 | 6 | 6 | 0.683 |

Total dimensions: `2634`

## Stack-Up Focus

Primary stack-up: `bolt_protrusion_at_flange_2_interface`

Key files:

- `stackup/stackup_relevant_dimensions.json`
- `stackup/stackup_relevant_dimensions.csv`

Selected stack-up dimensions:

| No. | Part | Dimension | Value |
|---:|---|---|---|
| 1 | Washer | Washer thickness C | Needs washer dash number confirmation |
| 2 | Rear/flange side | Flange/interface axial offset | 8.76 +/- 0.13 mm, source needs confirmation |
| 3 | Front case/flange side | Flange/interface axial offset | 5.08 +/- 0.13 mm |
| 4 | R10AS/bracket | Axial offset | 6.35 +/- 0.13 mm |
| 5 | R10AS/bracket | Axial offset | 6.10 +/- 0.13 mm |
| 6 | Bolt | Bolt length L, AS3580-5-22 | 34.925 +/- 0.254 mm |
| 7 | Nut | Nut height H, ST2780-09 | 4.318 +/- 0.508 mm |
| 8 | Interface chamfer | Chamfer length from UG | Requires CAD/UG measurement |

PPT reference result:

- Nominal bolt protrusion: `4.934 mm`
- Worst-case note: `3.6 threads`
- Direct stack thickness shown: `31.75 +/- 0.25 mm`

## Notes

- `config.local.json` contains the local Gemini key and is ignored by git.
- `.cache/` contains Gemini responses and is ignored by git.
- Items marked as needing confirmation should be reviewed before final engineering release.
