# Implementation Plan: Dimension Extraction System

## Overview

This implementation plan organizes tasks into 3 parallel workstreams to enable simultaneous development by multiple developers. The system is a Python-based tool that extracts dimensional data from engineering drawings using LLM vision APIs (GPT-4 Vision, Claude, Gemini).

**Architecture Components:**
- PDF Converter, Queue Manager, Extractor Core, API Router
- Retry Handler, Response Cache, Data Validator, Confidence Scorer

**Parallel Development Strategy:**
- **Developer 1**: Infrastructure & I/O (PDF conversion, file handling, configuration, logging)
- **Developer 2**: API Integration & Processing (API Router, Retry Handler, Cache, Queue Manager)
- **Developer 3**: Data Processing & Validation (Data models, Validator, Confidence Scorer, Extractor Core)

**Key Interfaces Between Workstreams:**
- Developer 1 → Developer 2: Image objects from PDF conversion
- Developer 2 → Developer 3: APIResponse objects from LLM APIs
- Developer 3 → Developer 1: ExtractionResult objects for JSON output

---

## Developer 1: Infrastructure & I/O

### 1. Set up project structure and dependencies
  - Create Python project structure (src/, tests/, docs/, config/)
  - Create requirements.txt with core dependencies (pdf2image, Pillow, jsonschema, tenacity, pytest, hypothesis)
  - Set up virtual environment and installation instructions
  - Create .gitignore for Python projects
  - _Requirements: 16.1, 18.1_

### 2. Implement PDF to Image Converter
  - [ ] 2.1 Create PDFConverter class with pdf2image integration
    - Implement convert_pdf_to_images() method
    - Handle single-page and multi-page PDFs
    - Set DPI to 300 minimum for quality
    - Return list of PIL Image objects
    - _Requirements: 16.1, 16.2, 16.3_
  
  - [ ]* 2.2 Write property test for PDF converter
    - **Property 11: Multi-Page PDF Completeness**
    - **Property 18: Image Resolution Preservation**
    - **Validates: Requirements 16.2, 16.3**
  
  - [ ] 2.3 Add error handling for encrypted/corrupted PDFs
    - Detect encrypted PDFs and skip with warning
    - Handle corrupted PDFs gracefully
    - Log skipped files with reasons
    - _Requirements: 16.4, 12.4_
  
  - [ ]* 2.4 Write unit tests for PDF converter edge cases
    - Test encrypted PDF handling
    - Test corrupted PDF handling
    - Test multi-page PDF processing
    - _Requirements: 16.4_

### 3. Implement configuration management
  - [ ] 3.1 Create ExtractorConfig dataclass
    - Define configuration structure (API settings, cache directory, DPI, etc.)
    - Implement load_from_file() method for YAML/JSON config files
    - Implement load_from_env() method for environment variables
    - _Requirements: 18.1, 18.2_
  
  - [ ] 3.2 Create APIConfig dataclass
    - Define API provider selection (gpt4, claude, gemini)
    - Store API credentials securely from environment variables
    - Implement credential validation
    - _Requirements: 18.1, 18.3_
  
  - [ ]* 3.3 Write unit tests for configuration loading
    - Test loading from config files
    - Test loading from environment variables
    - Test missing credential handling
    - _Requirements: 18.4_

### 4. Implement logging system
  - [ ] 4.1 Create structured logging with ErrorLog dataclass
    - Implement log_error() method with timestamp, error_type, severity, message, context
    - Configure logging to console and file
    - Implement log rotation for large log files
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_
  
  - [ ]* 4.2 Write property test for error logging
    - **Property 17: Error Logging Completeness**
    - **Validates: Requirements 11.5, 19.1, 19.2, 19.3, 19.4**
  
  - [ ] 4.3 Add API usage tracking to logs
    - Log API request/response counts
    - Log token consumption
    - Log estimated costs
    - Redact sensitive data from logs
    - _Requirements: 18.5, 19.2_

### 5. Implement JSON output generation
  - [ ] 5.1 Create JSONPrettyPrinter class
    - Implement print() method to write ExtractionOutput to JSON
    - Implement _objects_to_dict() conversion method
    - Format JSON with proper indentation and sorting
    - _Requirements: 8.1, 9.3_
  
  - [ ] 5.2 Implement JSON schema validation
    - Load JSON schema from file
    - Validate output against schema before writing
    - Return validation errors if schema check fails
    - _Requirements: 8.5, 9.5_
  
  - [ ]* 5.3 Write property test for JSON output
    - **Property 1: JSON Round-Trip Preservation**
    - **Property 13: JSON Schema Compliance**
    - **Property 14: Output Completeness**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 9.3, 9.4**

### 6. Implement JSON parser
  - [ ] 6.1 Create JSONParser class
    - Implement parse() method to read JSON files
    - Implement _dict_to_objects() conversion method
    - Validate JSON against schema before parsing
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ]* 6.2 Write unit tests for JSON parser
    - Test parsing valid JSON files
    - Test error handling for invalid JSON
    - Test schema validation failures
    - _Requirements: 9.2_

### 7. Implement human review report generation
  - [ ] 7.1 Create HumanReviewReport class
    - Generate human-readable report from ExtractionResult
    - Highlight extractions with confidence < 0.8
    - Display extracted dimensions with source locations
    - Format report as HTML or Markdown
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [ ]* 7.2 Write unit tests for review report generation
    - Test report formatting
    - Test confidence threshold highlighting
    - Test source location display
    - _Requirements: 14.1, 14.2, 14.3_

### 8. Checkpoint - Developer 1
  - Ensure all tests pass, ask the user if questions arise.

---

## Developer 2: API Integration & Processing

### 9. Implement API Router foundation
  - [ ] 9.1 Create APIRouter class with provider selection
    - Implement __init__() with APIConfig
    - Implement provider selection logic (gpt4, claude, gemini)
    - Create unified APIResponse dataclass
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 9.2 Create base API adapter interface
    - Define abstract base class for API adapters
    - Define common methods: call_api(), format_request(), parse_response()
    - _Requirements: 10.1, 10.2, 10.3_

### 10. Implement GPT-4 Vision adapter
  - [ ] 10.1 Create GPT4VisionAdapter class
    - Implement call_api() using OpenAI SDK
    - Implement image encoding (base64)
    - Implement structured output via function calling
    - Parse response into APIResponse format
    - _Requirements: 10.1_
  
  - [ ]* 10.2 Write unit tests for GPT-4 adapter
    - Mock OpenAI API calls
    - Test request formatting
    - Test response parsing
    - Test error handling
    - _Requirements: 10.1_

### 11. Implement Claude Vision adapter
  - [ ] 11.1 Create ClaudeVisionAdapter class
    - Implement call_api() using Anthropic SDK
    - Implement image encoding (base64)
    - Implement message content blocks for vision
    - Parse response into APIResponse format
    - _Requirements: 10.2_
  
  - [ ]* 11.2 Write unit tests for Claude adapter
    - Mock Anthropic API calls
    - Test request formatting
    - Test response parsing
    - Test error handling
    - _Requirements: 10.2_

### 12. Implement Gemini Vision adapter
  - [ ] 12.1 Create GeminiVisionAdapter class
    - Implement call_api() using Google Generative AI SDK
    - Implement multimodal input (text + images)
    - Parse response into APIResponse format
    - _Requirements: 10.3_
  
  - [ ]* 12.2 Write unit tests for Gemini adapter
    - Mock Google API calls
    - Test request formatting
    - Test response parsing
    - Test error handling
    - _Requirements: 10.3_

### 13. Implement Retry Handler
  - [ ] 13.1 Create RetryHandler class with exponential backoff
    - Implement call_with_retry() using tenacity library
    - Configure exponential backoff with jitter
    - Handle rate limit errors (429) with Retry-After header
    - Handle timeout errors with 3 retry attempts
    - Handle authentication errors (no retry)
    - _Requirements: 10.5, 11.1, 11.2, 11.3_
  
  - [ ]* 13.2 Write property tests for retry behavior
    - **Property 9: Retry Behavior for Rate Limits**
    - **Property 10: Retry Behavior for Timeouts**
    - **Validates: Requirements 11.1, 11.3**
  
  - [ ]* 13.3 Write unit tests for retry handler
    - Test exponential backoff timing
    - Test Retry-After header handling
    - Test authentication error (no retry)
    - Test max retry limit
    - _Requirements: 11.1, 11.2, 11.3_

### 14. Implement Response Cache
  - [ ] 14.1 Create ResponseCache class
    - Implement cache storage using file-based persistence
    - Implement cache key generation using image hash
    - Implement get() and set() methods
    - Implement cache invalidation based on config changes
    - _Requirements: 20.1_
  
  - [ ]* 14.2 Write property test for cache behavior
    - **Property 8: Cache Hit for Identical Inputs**
    - **Validates: Requirements 20.1**
  
  - [ ]* 14.3 Write unit tests for cache operations
    - Test cache hit/miss scenarios
    - Test cache persistence across sessions
    - Test cache invalidation
    - _Requirements: 20.1_

### 15. Implement Processing Queue Manager
  - [ ] 15.1 Create QueueManager class
    - Implement add_file() to enqueue files
    - Implement get_next() to dequeue files
    - Track processing status (pending, in-progress, completed, failed)
    - Implement progress calculation (M/N * 100)
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [ ]* 15.2 Write property tests for queue manager
    - **Property 7: Failure Isolation in Batch Processing**
    - **Property 12: Progress Calculation Accuracy**
    - **Validates: Requirements 11.4, 12.3, 12.4**
  
  - [ ]* 15.3 Write unit tests for queue operations
    - Test file enqueueing/dequeueing
    - Test status tracking
    - Test progress reporting
    - Test failure isolation
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

### 16. Integrate API Router with Retry Handler and Cache
  - [ ] 16.1 Wire APIRouter to use RetryHandler
    - Wrap all API calls with retry logic
    - Log retry attempts
    - _Requirements: 10.5, 11.1, 11.3_
  
  - [ ] 16.2 Wire APIRouter to use ResponseCache
    - Check cache before making API calls
    - Store responses in cache after successful calls
    - Skip cache for failed requests
    - _Requirements: 20.1_
  
  - [ ] 16.3 Implement extract_from_image() orchestration method
    - Check cache first
    - Route to appropriate provider adapter
    - Apply retry logic
    - Store result in cache
    - Return unified APIResponse
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

### 17. Implement API usage tracking
  - [ ] 17.1 Add usage statistics to APIRouter
    - Track request counts per provider
    - Track token consumption
    - Estimate API costs based on provider pricing
    - _Requirements: 18.5, 20.5_
  
  - [ ]* 17.2 Write unit tests for usage tracking
    - Test request counting
    - Test token tracking
    - Test cost estimation
    - _Requirements: 18.5_

### 18. Checkpoint - Developer 2
  - Ensure all tests pass, ask the user if questions arise.

---

## Developer 3: Data Processing & Validation

### 19. Implement core data models
  - [ ] 19.1 Create data model classes
    - Implement Dimension dataclass
    - Implement Tolerance dataclass with ToleranceType enum
    - Implement GDTCallout dataclass with GDTSymbol and MaterialCondition enums
    - Implement Datum dataclass
    - Implement MaterialSpec dataclass
    - Implement AssemblyRelationship dataclass with RelationshipType enum
    - Implement DimensionalChain and ChainLink dataclasses
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1_
  
  - [ ] 19.2 Create result container classes
    - Implement ExtractionResult dataclass
    - Implement AssemblyResult dataclass
    - Implement BatchResult dataclass
    - Implement ValidationResult dataclass
    - _Requirements: 8.1, 12.5_
  
  - [ ]* 19.3 Write unit tests for data models
    - Test dataclass instantiation
    - Test enum values
    - Test field validation
    - _Requirements: 1.1, 2.1, 3.1, 4.1_

### 20. Implement Data Validator
  - [ ] 20.1 Create DataValidator class foundation
    - Implement validate_dimension() method
    - Implement validate_tolerance() method
    - Implement validate_datum_references() method
    - Implement validate_units() method
    - Return ValidationResult with warnings/errors
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  
  - [ ]* 20.2 Write property tests for validator
    - **Property 3: Referential Integrity**
    - **Property 4: Tolerance Magnitude Validation**
    - **Property 5: Unit Consistency Within Parts**
    - **Property 16: Missing Tolerance Flagging**
    - **Validates: Requirements 1.2, 2.3, 2.5, 3.4, 4.4, 13.1, 13.2, 13.3**
  
  - [ ]* 20.3 Write unit tests for validation rules
    - Test tolerance < nominal validation
    - Test datum reference validation
    - Test unit consistency validation
    - Test missing tolerance flagging
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

### 21. Implement Confidence Scorer
  - [ ] 21.1 Create ConfidenceScorer class
    - Implement score_dimension() method
    - Implement score_extraction_result() method
    - Implement _combine_scores() to merge LLM and validation scores
    - Ensure all scores are in [0.0, 1.0] range
    - Reduce scores for validation failures
    - _Requirements: 1.4, 2.4, 3.5, 4.5, 5.5, 6.5, 15.1, 15.2, 15.3_
  
  - [ ]* 21.2 Write property tests for confidence scorer
    - **Property 2: Confidence Score Range Invariant**
    - **Property 6: Validation Failure Reduces Confidence**
    - **Property 19: Confidence Score Threshold Flagging**
    - **Validates: Requirements 1.4, 2.4, 3.5, 4.5, 13.4, 15.1, 15.3, 15.5**
  
  - [ ]* 21.3 Write unit tests for confidence scoring
    - Test score combination logic
    - Test validation failure impact
    - Test threshold flagging (< 0.7)
    - _Requirements: 15.1, 15.2, 15.3, 15.5_

### 22. Implement Dimension Extractor Core - Part 1 (Prompt Construction)
  - [ ] 22.1 Create DimensionExtractor class foundation
    - Implement __init__() with config, api_router, validator, confidence_scorer, cache
    - Create prompt templates for dimension extraction
    - Create prompt templates for GD&T extraction
    - Create prompt templates for assembly relationship extraction
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_
  
  - [ ] 22.2 Implement prompt construction methods
    - Implement _build_dimension_prompt() with domain-specific instructions
    - Implement _build_assembly_prompt() for PNG diagrams
    - Include examples in prompts for better LLM performance
    - _Requirements: 1.1, 2.1, 3.1, 4.1_

### 23. Implement Dimension Extractor Core - Part 2 (Response Parsing)
  - [ ] 23.1 Implement LLM response parsing
    - Implement _parse_dimension_response() to extract Dimension objects
    - Implement _parse_tolerance_response() to extract Tolerance objects
    - Implement _parse_gdt_response() to extract GDTCallout objects
    - Implement _parse_datum_response() to extract Datum objects
    - Implement _parse_material_response() to extract MaterialSpec objects
    - Handle unparseable responses with retry and low confidence flagging
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 5.1, 5.2_
  
  - [ ]* 23.2 Write unit tests for response parsing
    - Test parsing valid LLM responses
    - Test handling unparseable responses
    - Test extraction of all data types
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

### 24. Implement Dimension Extractor Core - Part 3 (Processing Methods)
  - [ ] 24.1 Implement process_pdf() method
    - Convert PDF to images (call PDFConverter)
    - Send images to API Router with dimension extraction prompt
    - Parse API responses into structured data
    - Validate extracted data
    - Calculate confidence scores
    - Return ExtractionResult
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 16.1, 16.3_
  
  - [ ] 24.2 Implement process_assembly_diagram() method
    - Send PNG to API Router with assembly extraction prompt
    - Parse assembly relationships
    - Link part identifiers to drawing files
    - Return AssemblyResult
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 17.1, 17.2, 17.3, 17.4_
  
  - [ ]* 24.3 Write integration tests for processing methods
    - Test end-to-end PDF processing with mock API
    - Test end-to-end assembly processing with mock API
    - Test error handling for API failures
    - _Requirements: 16.1, 17.1_

### 25. Implement Dimension Extractor Core - Part 4 (Batch Processing)
  - [ ] 25.1 Implement process_batch() method
    - Use QueueManager to track files
    - Process each file sequentially
    - Isolate failures (continue on error)
    - Generate BatchResult with success/failure summary
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ]* 25.2 Write property test for batch processing
    - **Property 7: Failure Isolation in Batch Processing**
    - **Validates: Requirements 11.4, 12.4**

### 26. Implement dimensional chain identification
  - [ ] 26.1 Implement identify_dimensional_chains() method
    - Identify bolt protrusion depth as primary chain
    - Identify contributing dimensions from assembly relationships
    - Determine contribution signs (+1 or -1)
    - Rank dimensions by contribution importance
    - Calculate total_nominal, worst_case_max, worst_case_min
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 26.2 Write property test for dimensional chains
    - **Property 15: Dimensional Chain Sign Consistency**
    - **Validates: Requirements 7.3**
  
  - [ ]* 26.3 Write unit tests for chain identification
    - Test chain identification logic
    - Test contribution sign determination
    - Test worst-case calculations
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

### 27. Implement unit preservation and validation
  - [ ] 27.1 Add unit preservation to all extraction methods
    - Ensure units are preserved unchanged from source
    - Validate unit consistency within parts
    - _Requirements: 1.5, 13.3_
  
  - [ ]* 27.2 Write property test for unit preservation
    - **Property 20: Unit Preservation**
    - **Validates: Requirements 1.5**

### 28. Checkpoint - Developer 3
  - Ensure all tests pass, ask the user if questions arise.

---

## Integration & Final Assembly

### 29. Wire all components together
  - [ ] 29.1 Create main entry point (main.py or CLI)
    - Parse command-line arguments (input files, config file, output directory)
    - Load configuration
    - Initialize DimensionExtractor with all dependencies
    - Call process_batch() or process_pdf()
    - Write JSON output
    - Generate human review report
    - _Requirements: 8.1, 12.1, 14.1_
  
  - [ ] 29.2 Add command-line interface
    - Implement argparse for CLI arguments
    - Support batch mode and single-file mode
    - Support config file specification
    - Display progress during processing
    - _Requirements: 12.1, 12.3_
  
  - [ ]* 29.3 Write integration tests for CLI
    - Test CLI argument parsing
    - Test batch processing via CLI
    - Test single-file processing via CLI
    - _Requirements: 12.1_

### 30. Implement cost estimation
  - [ ] 30.1 Add cost estimation before processing
    - Estimate API costs based on file count and image sizes
    - Display cost estimate to user
    - Require confirmation before proceeding
    - _Requirements: 20.5_
  
  - [ ]* 30.2 Write unit tests for cost estimation
    - Test cost calculation logic
    - Test cost display formatting
    - _Requirements: 20.5_

### 31. Implement manual correction support
  - [ ] 31.1 Add support for corrected JSON input
    - Implement load_corrected_json() method
    - Merge manual corrections with extracted data
    - Regenerate output with corrections
    - _Requirements: 14.4, 14.5_
  
  - [ ]* 31.2 Write unit tests for manual corrections
    - Test loading corrected JSON
    - Test merging corrections
    - Test regenerating output
    - _Requirements: 14.4, 14.5_

### 32. Add image optimization
  - [ ] 32.1 Implement image compression
    - Compress images to minimum resolution for accuracy
    - Balance quality vs. API cost
    - _Requirements: 20.2_
  
  - [ ] 32.2 Implement title block caching
    - Detect identical title blocks across pages
    - Extract once and reuse
    - _Requirements: 20.3_
  
  - [ ]* 32.3 Write unit tests for image optimization
    - Test compression quality
    - Test title block detection
    - _Requirements: 20.2, 20.3_

### 33. Final integration testing
  - [ ]* 33.1 Run end-to-end tests with sample drawings
    - Test with provided sample PDFs (5377630-01-Front_case.pdf, etc.)
    - Test with assembly diagram (Assemble_Diagram.png)
    - Verify JSON output structure
    - Verify dimensional chain identification
    - _Requirements: All_
  
  - [ ]* 33.2 Run all property-based tests
    - Execute all 20 property tests with 100+ iterations each
    - Verify all properties hold
    - _Requirements: All_

### 34. Documentation and deployment preparation
  - [ ] 34.1 Write README.md
    - Installation instructions
    - Configuration guide
    - Usage examples
    - API credential setup
  
  - [ ] 34.2 Write API documentation
    - Document all public classes and methods
    - Include code examples
    - Document JSON schema
  
  - [ ] 34.3 Create example configuration files
    - Example config.yaml
    - Example .env file
    - Example API credential setup

### 35. Set up CI/CD pipeline
  - [ ] 35.1 Create GitHub Actions workflow
    - Run unit tests on every PR
    - Run property-based tests on every PR
    - Run linting (flake8, black, mypy)
    - Generate test coverage reports
  
  - [ ] 35.2 Set up branch protection rules
    - Require PR reviews before merge
    - Require passing tests before merge
    - Require up-to-date branches

### 36. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (20 properties defined in design)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The 3 workstreams can proceed in parallel with minimal dependencies
- Key integration points are clearly marked (Developer 1→2, 2→3, 3→1)
- GitHub workflow: Each developer works on feature branches, creates PRs for review
- CI/CD pipeline ensures code quality and test coverage before merging

## GitHub Workflow Recommendations

**Branch Strategy:**
- `main` branch: production-ready code
- `dev` branch: integration branch for all features
- Feature branches: `dev1/pdf-converter`, `dev2/api-router`, `dev3/validator`, etc.

**PR Strategy:**
- Each task or small group of related tasks = 1 PR
- PRs should be reviewed by at least one other developer
- All tests must pass before merging
- Keep PRs small and focused for easier review

**Parallel Development:**
- Developers can work independently on their workstreams
- Use interface contracts (dataclasses) to define boundaries
- Mock dependencies during development
- Integration happens in `dev` branch after individual components are complete
