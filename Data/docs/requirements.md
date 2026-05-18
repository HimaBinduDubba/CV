# Requirements Document

## Introduction

The Dimension Extraction System is an automated tool for extracting dimensional and tolerance data from engineering drawings (PDF format) to enable tolerance stack-up analysis. The system uses LLM-based computer vision APIs (GPT-4 Vision, Claude, Gemini) to parse engineering drawings and extract all dimensions, tolerances, GD&T callouts, datum references, and material specifications relevant to dimensional chain analysis. The primary use case is analyzing bolt protrusion depth in mechanical assemblies.

## Glossary

- **Dimension_Extractor**: The system component that processes engineering drawings and extracts dimensional data
- **Engineering_Drawing**: A PDF document containing technical drawings with dimensions, tolerances, and GD&T annotations
- **Nominal_Dimension**: The target or ideal dimension value (e.g., 50mm, 100mm)
- **Tolerance**: The permissible variation from the nominal dimension (e.g., ±0.1mm, +0.2/-0.1)
- **GD&T**: Geometric Dimensioning and Tolerancing - symbols and callouts defining geometric characteristics (flatness, perpendicularity, etc.)
- **Datum_Reference**: A theoretically exact point, axis, or plane used as a reference for measurements (labeled A, B, C, etc.)
- **Stack_Up_Analysis**: Calculation of cumulative dimensional variation through a chain of related dimensions
- **Dimensional_Chain**: A sequence of related dimensions that contribute to a critical measurement
- **Confidence_Score**: A numerical value (0-1) indicating the system's certainty in extracted data
- **LLM_API**: Large Language Model Application Programming Interface (GPT-4 Vision, Claude, Gemini)
- **Assembly_Diagram**: A visual representation showing how parts fit together
- **Bolt_Protrusion_Depth**: The distance a bolt extends beyond the assembly surface (primary dimensional chain)
- **Extraction_Context**: Metadata describing what a dimension measures, which part it belongs to, and its relationship to other dimensions

## Requirements

### Requirement 1: Extract Nominal Dimensions

**User Story:** As a mechanical engineer, I want the system to extract all nominal dimensions from engineering drawings, so that I can identify the target values for stack-up analysis.

#### Acceptance Criteria

1. WHEN an Engineering_Drawing is provided, THE Dimension_Extractor SHALL extract all Nominal_Dimension values with their units
2. THE Dimension_Extractor SHALL associate each Nominal_Dimension with its corresponding part identifier
3. THE Dimension_Extractor SHALL identify the feature or surface that each Nominal_Dimension measures
4. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted Nominal_Dimension
5. FOR ALL extracted Nominal_Dimension values, the system SHALL preserve the original unit of measurement (mm, inches, etc.)

### Requirement 2: Extract Tolerance Values

**User Story:** As a mechanical engineer, I want the system to extract tolerance values associated with dimensions, so that I can calculate worst-case stack-up scenarios.

#### Acceptance Criteria

1. WHEN a dimension with Tolerance is encountered, THE Dimension_Extractor SHALL extract both the Tolerance type and values
2. THE Dimension_Extractor SHALL distinguish between bilateral tolerances (±0.1mm), unilateral tolerances (+0.2/-0.1), and limit dimensions
3. THE Dimension_Extractor SHALL link each Tolerance to its corresponding Nominal_Dimension
4. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted Tolerance
5. IF a dimension lacks an explicit Tolerance, THEN THE Dimension_Extractor SHALL flag it as missing tolerance data

### Requirement 3: Extract GD&T Callouts

**User Story:** As a mechanical engineer, I want the system to extract GD&T symbols and callouts, so that I can account for geometric variations in stack-up analysis.

#### Acceptance Criteria

1. WHEN GD&T symbols are present in an Engineering_Drawing, THE Dimension_Extractor SHALL identify and extract the symbol type (flatness, perpendicularity, parallelism, position, etc.)
2. THE Dimension_Extractor SHALL extract the tolerance zone value associated with each GD&T callout
3. THE Dimension_Extractor SHALL extract any material condition modifiers (MMC, LMC, RFS)
4. THE Dimension_Extractor SHALL link each GD&T callout to the feature it controls
5. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted GD&T callout

### Requirement 4: Extract Datum References

**User Story:** As a mechanical engineer, I want the system to extract datum references, so that I can understand the measurement reference framework for each part.

#### Acceptance Criteria

1. WHEN Datum_Reference labels are present in an Engineering_Drawing, THE Dimension_Extractor SHALL extract all datum identifiers (A, B, C, etc.)
2. THE Dimension_Extractor SHALL identify the feature or surface associated with each Datum_Reference
3. THE Dimension_Extractor SHALL extract datum precedence order when specified in GD&T feature control frames
4. THE Dimension_Extractor SHALL link dimensions and GD&T callouts to their referenced datums
5. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted Datum_Reference

### Requirement 5: Extract Material Specifications

**User Story:** As a mechanical engineer, I want the system to extract material specifications from drawings, so that I can account for material-dependent variations (thermal expansion, compliance, etc.).

#### Acceptance Criteria

1. WHEN material specifications are present in an Engineering_Drawing, THE Dimension_Extractor SHALL extract material type and grade
2. THE Dimension_Extractor SHALL extract surface finish specifications when present
3. THE Dimension_Extractor SHALL extract heat treatment requirements when specified
4. THE Dimension_Extractor SHALL associate material specifications with the corresponding part
5. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted material specification

### Requirement 6: Parse Assembly Relationships

**User Story:** As a mechanical engineer, I want the system to understand how parts relate to each other in the assembly, so that I can construct accurate dimensional chains.

#### Acceptance Criteria

1. WHEN an Assembly_Diagram is provided, THE Dimension_Extractor SHALL identify all parts in the assembly
2. THE Dimension_Extractor SHALL extract mating relationships between parts (which surfaces contact each other)
3. THE Dimension_Extractor SHALL identify the assembly sequence or stacking order
4. THE Dimension_Extractor SHALL link part identifiers from the Assembly_Diagram to corresponding Engineering_Drawing files
5. THE Dimension_Extractor SHALL assign a Confidence_Score to each extracted assembly relationship

### Requirement 7: Identify Dimensional Chains

**User Story:** As a mechanical engineer, I want the system to identify dimensional chains relevant to stack-up analysis, so that I can focus on critical measurements.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL identify the Bolt_Protrusion_Depth as the primary Dimensional_Chain
2. THE Dimension_Extractor SHALL identify all dimensions that contribute to the Bolt_Protrusion_Depth calculation
3. THE Dimension_Extractor SHALL determine whether each dimension adds to or subtracts from the Dimensional_Chain
4. THE Dimension_Extractor SHALL rank dimensions by their contribution to the critical measurement
5. WHERE multiple Dimensional_Chain paths exist, THE Dimension_Extractor SHALL identify all alternative paths

### Requirement 8: Generate JSON Output

**User Story:** As a software developer, I want the system to output extracted data in a structured JSON format, so that I can integrate it with downstream stack-up calculation tools.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL output all extracted data in valid JSON format
2. THE JSON output SHALL include Extraction_Context for each dimension (what it measures, which part, relationships)
3. THE JSON output SHALL include Confidence_Score values for all extracted data
4. THE JSON output SHALL include source references (page number, drawing number, zone) for each extracted element
5. THE JSON output SHALL be schema-validated before being returned to the user

### Requirement 9: Parse JSON Output Format

**User Story:** As a software developer, I want a parser that can read the JSON output format, so that I can programmatically access extracted dimension data.

#### Acceptance Criteria

1. WHEN a valid JSON output file is provided, THE JSON_Parser SHALL parse it into a structured data object
2. WHEN an invalid JSON output file is provided, THE JSON_Parser SHALL return a descriptive error message
3. THE JSON_Pretty_Printer SHALL format structured data objects back into valid JSON files
4. FOR ALL valid structured data objects, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
5. THE JSON_Parser SHALL validate the JSON schema before parsing

### Requirement 10: Integrate with LLM APIs

**User Story:** As a system administrator, I want the system to use LLM APIs for vision processing, so that I can leverage state-of-the-art computer vision without building custom models.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL support GPT-4 Vision API integration
2. THE Dimension_Extractor SHALL support Claude Vision API integration
3. THE Dimension_Extractor SHALL support Gemini Vision API integration
4. WHERE multiple LLM_API options are available, THE Dimension_Extractor SHALL allow API selection via configuration
5. WHEN an LLM_API call fails, THE Dimension_Extractor SHALL retry with exponential backoff up to 3 attempts

### Requirement 11: Handle API Errors

**User Story:** As a system administrator, I want the system to handle API errors gracefully, so that temporary failures do not crash the extraction process.

#### Acceptance Criteria

1. IF an LLM_API returns a rate limit error, THEN THE Dimension_Extractor SHALL wait and retry according to the API's rate limit guidance
2. IF an LLM_API returns an authentication error, THEN THE Dimension_Extractor SHALL log the error and terminate with a clear error message
3. IF an LLM_API returns a timeout error, THEN THE Dimension_Extractor SHALL retry the request up to 3 times
4. IF all retry attempts fail, THEN THE Dimension_Extractor SHALL log the failure and continue processing remaining drawings
5. THE Dimension_Extractor SHALL log all API errors with timestamps and request details

### Requirement 12: Process Multiple Drawing Files

**User Story:** As a mechanical engineer, I want the system to process multiple engineering drawings in batch, so that I can extract data from all parts in an assembly efficiently.

#### Acceptance Criteria

1. WHEN multiple Engineering_Drawing files are provided, THE Dimension_Extractor SHALL process each file sequentially
2. THE Dimension_Extractor SHALL maintain a processing queue for all input files
3. THE Dimension_Extractor SHALL report progress as a percentage of files processed
4. IF processing one file fails, THEN THE Dimension_Extractor SHALL continue processing remaining files
5. THE Dimension_Extractor SHALL generate a summary report listing successfully processed and failed files

### Requirement 13: Validate Extracted Data

**User Story:** As a mechanical engineer, I want the system to validate extracted data against engineering rules, so that I can identify potential extraction errors.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL validate that Tolerance values are smaller than their corresponding Nominal_Dimension values
2. THE Dimension_Extractor SHALL validate that all Datum_Reference labels referenced in GD&T callouts are defined in the drawing
3. THE Dimension_Extractor SHALL validate that dimension units are consistent within each part
4. IF validation fails, THEN THE Dimension_Extractor SHALL flag the data with a warning and reduced Confidence_Score
5. THE Dimension_Extractor SHALL generate a validation report listing all warnings and errors

### Requirement 14: Support Human Review

**User Story:** As a mechanical engineer, I want to review and correct extracted data, so that I can ensure accuracy before performing stack-up calculations.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL generate a human-readable review report alongside the JSON output
2. THE review report SHALL highlight all extractions with Confidence_Score below 0.8
3. THE review report SHALL display extracted dimensions alongside their source location in the drawing
4. WHERE manual corrections are needed, THE Dimension_Extractor SHALL accept a corrected JSON file as input
5. THE Dimension_Extractor SHALL merge manual corrections with extracted data and regenerate the output

### Requirement 15: Calculate Confidence Scores

**User Story:** As a mechanical engineer, I want confidence scores for all extracted data, so that I can prioritize manual review of uncertain extractions.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL calculate a Confidence_Score (0.0 to 1.0) for each extracted data element
2. THE Confidence_Score SHALL be based on LLM_API response confidence and validation results
3. THE Dimension_Extractor SHALL assign lower Confidence_Score values to data that fails validation checks
4. THE Dimension_Extractor SHALL calculate an overall Confidence_Score for each Engineering_Drawing
5. THE Dimension_Extractor SHALL flag any extraction with Confidence_Score below 0.7 for mandatory human review

### Requirement 16: Handle PDF Input Files

**User Story:** As a mechanical engineer, I want the system to accept PDF engineering drawings as input, so that I can use standard industry file formats.

#### Acceptance Criteria

1. WHEN a PDF file is provided, THE Dimension_Extractor SHALL convert it to an image format compatible with LLM_API vision endpoints
2. THE Dimension_Extractor SHALL preserve image resolution sufficient for reading dimension text (minimum 300 DPI)
3. THE Dimension_Extractor SHALL process multi-page PDF files by extracting each page separately
4. IF a PDF file is encrypted or password-protected, THEN THE Dimension_Extractor SHALL request credentials or skip the file
5. THE Dimension_Extractor SHALL support PDF files up to 50 pages in length

### Requirement 17: Handle PNG Assembly Diagrams

**User Story:** As a mechanical engineer, I want the system to accept PNG assembly diagrams as input, so that I can provide assembly context in common image formats.

#### Acceptance Criteria

1. WHEN a PNG Assembly_Diagram is provided, THE Dimension_Extractor SHALL process it using LLM_API vision capabilities
2. THE Dimension_Extractor SHALL extract part labels and identifiers from the Assembly_Diagram
3. THE Dimension_Extractor SHALL identify assembly relationships and mating surfaces
4. THE Dimension_Extractor SHALL link Assembly_Diagram part identifiers to Engineering_Drawing file names
5. THE Dimension_Extractor SHALL assign a Confidence_Score to assembly relationship extractions

### Requirement 18: Configure API Credentials

**User Story:** As a system administrator, I want to configure LLM API credentials securely, so that I can authenticate with vision services without hardcoding secrets.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL read LLM_API credentials from environment variables
2. THE Dimension_Extractor SHALL support configuration file-based credential management
3. THE Dimension_Extractor SHALL validate API credentials before processing drawings
4. IF API credentials are missing or invalid, THEN THE Dimension_Extractor SHALL terminate with a clear error message
5. THE Dimension_Extractor SHALL log API usage statistics (number of requests, tokens consumed) for cost tracking

### Requirement 19: Generate Extraction Logs

**User Story:** As a system administrator, I want detailed logs of the extraction process, so that I can troubleshoot issues and audit system behavior.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL log the start and end time of each drawing processing operation
2. THE Dimension_Extractor SHALL log all LLM_API requests and responses (with sensitive data redacted)
3. THE Dimension_Extractor SHALL log all validation warnings and errors
4. THE Dimension_Extractor SHALL log Confidence_Score calculations and their contributing factors
5. THE Dimension_Extractor SHALL write logs to a configurable file location with timestamps

### Requirement 20: Optimize API Usage

**User Story:** As a system administrator, I want the system to minimize API costs, so that I can process drawings efficiently without excessive spending.

#### Acceptance Criteria

1. THE Dimension_Extractor SHALL cache LLM_API responses for identical input images
2. THE Dimension_Extractor SHALL compress images to the minimum resolution required for accurate extraction
3. WHERE multiple pages contain identical title blocks, THE Dimension_Extractor SHALL extract title block data once and reuse it
4. THE Dimension_Extractor SHALL batch multiple extraction requests when the LLM_API supports batching
5. THE Dimension_Extractor SHALL report estimated API costs before processing a batch of drawings
