# Requirements Document

## Introduction

This document specifies requirements for upgrading the Blind Spot Risk Index (BSRI) documentation from V2 to V3. The upgrade addresses technical accuracy issues, regulatory standard misattributions, missing provenance information, and inconsistencies in parameter definitions and worked examples. The V3 documentation will maintain the existing multiplicative formula while improving clarity, correctness, and traceability of all parameters and citations.

## Glossary

- **BSRI_Document**: The Blind Spot Risk Index documentation that defines the safety metric and its calculation methodology
- **Parameter_Classification_System**: A three-tier categorization system (Standard, Vehicle, Engineering) that organizes BSRI parameters by their source and nature
- **Provenance_Table**: A comprehensive table mapping each BSRI parameter to its authoritative source (regulatory standard, engineering calculation, or vehicle specification)
- **ISO_15622**: Adaptive Cruise Control (ACC) standard - incorrectly cited in V2 for blind spot parameters
- **UNECE_R151**: Blind Spot Information System (BSIS) regulation for detecting vehicles alongside
- **UNECE_R158**: Reversing camera/monitor regulation
- **UNECE_R159**: Moving Off Information System (MOIS) regulation for low-speed forward detection
- **W_vru**: Vulnerable Road User (VRU) detection width parameter
- **SWEPT_PATH_LEFT**: The swept path boundary on the left side of the vehicle during turning maneuvers
- **SWEPT_PATH_RIGHT**: The swept path boundary on the right side of the vehicle during turning maneuvers
- **Special_Cases**: The five specific BSRI edge cases (static obstacles, pedestrians at speed, cyclists in zone, door opening, reversing) requiring distinct labeling
- **Worked_Example**: A complete step-by-step calculation demonstrating BSRI computation with real vehicle parameters
- **Sensor_Sources**: Documentation identifying which physical sensors (cameras, radar, ultrasonic) contribute to each formula term
- **Multiplicative_Formula**: The existing BSRI calculation approach using product of risk factors
- **Calibration_Data**: Empirical validation data linking BSRI scores to real-world collision outcomes
- **V2_Document**: The current version of BSRI documentation containing the identified issues
- **V3_Document**: The new version of BSRI documentation addressing all identified issues

## Requirements

### Requirement 1: Parameter Classification System

**User Story:** As a technical reviewer, I want parameters organized by classification tier, so that I can quickly understand parameter sources and application contexts

#### Acceptance Criteria

1. THE BSRI_Document SHALL define three classification tiers: Standard, Vehicle, and Engineering
2. THE BSRI_Document SHALL classify each parameter as exactly one of Standard, Vehicle, or Engineering
3. THE BSRI_Document SHALL document Standard parameters as values derived from regulatory standards
4. THE BSRI_Document SHALL document Vehicle parameters as values specific to individual vehicle models
5. THE BSRI_Document SHALL document Engineering parameters as values derived from calculations or design assumptions

### Requirement 2: Remove ISO 15622 Misattribution

**User Story:** As a safety engineer, I want ISO 15622 removed from blind spot citations, so that the documentation references only applicable standards

#### Acceptance Criteria

1. THE BSRI_Document SHALL NOT cite ISO 15622 in relation to blind spot detection parameters
2. WHERE ISO 15622 was previously cited for blind spot parameters, THE BSRI_Document SHALL substitute the correct regulatory reference or mark as Engineering parameter
3. THE BSRI_Document SHALL include ISO 15622 only if explicitly describing Adaptive Cruise Control contexts

### Requirement 3: Correct UNECE Regulation Scope

**User Story:** As a regulatory compliance officer, I want UNECE regulations correctly scoped, so that I can verify compliance claims accurately

#### Acceptance Criteria

1. THE BSRI_Document SHALL cite UNECE R151 only for lateral blind spot detection (vehicles alongside)
2. THE BSRI_Document SHALL cite UNECE R158 only for reversing camera/monitor requirements
3. THE BSRI_Document SHALL cite UNECE R159 only for Moving Off Information System (low-speed forward detection)
4. THE BSRI_Document SHALL NOT extend the scope of UNECE R151, R158, or R159 beyond their defined regulatory domains

### Requirement 4: W_vru Attribution Correction

**User Story:** As a VRU safety analyst, I want W_vru correctly attributed, so that I can trace its origin and validate its appropriateness

#### Acceptance Criteria

1. THE BSRI_Document SHALL remove any incorrect attribution of W_vru to ISO 15622
2. WHERE W_vru has a regulatory source, THE BSRI_Document SHALL cite the correct standard with section reference
3. WHERE W_vru lacks a regulatory source, THE BSRI_Document SHALL classify it as an Engineering parameter with documented rationale

### Requirement 5: Symmetric SWEPT_PATH Definition

**User Story:** As a geometric analyst, I want SWEPT_PATH_LEFT defined symmetrically to SWEPT_PATH_RIGHT, so that turning calculations are consistent in both directions

#### Acceptance Criteria

1. THE BSRI_Document SHALL define SWEPT_PATH_LEFT using the same geometric principles as SWEPT_PATH_RIGHT
2. THE BSRI_Document SHALL document SWEPT_PATH_LEFT with the same level of detail as SWEPT_PATH_RIGHT
3. WHERE SWEPT_PATH_RIGHT includes formulas, diagrams, or worked examples, THE BSRI_Document SHALL provide equivalent content for SWEPT_PATH_LEFT

### Requirement 6: Complete Provenance Table

**User Story:** As a safety researcher, I want a complete provenance table, so that I can verify the source of every parameter in the BSRI calculation

#### Acceptance Criteria

1. THE BSRI_Document SHALL include a Provenance_Table listing every parameter used in BSRI calculations
2. THE Provenance_Table SHALL identify the authoritative source for each parameter (regulatory standard with section, vehicle specification, or engineering calculation)
3. WHERE a parameter has no regulatory source, THE Provenance_Table SHALL document the engineering rationale or design assumption
4. THE Provenance_Table SHALL include the classification tier (Standard, Vehicle, Engineering) for each parameter

### Requirement 7: Complete References Table

**User Story:** As a documentation maintainer, I want a complete references table, so that all cited standards can be easily located and verified

#### Acceptance Criteria

1. THE BSRI_Document SHALL include a References section listing all cited standards and documents
2. THE References section SHALL include the full title for each cited standard
3. THE References section SHALL include the publication date or version for each cited standard
4. WHERE a standard is cited in the document, THE References section SHALL contain a corresponding entry

### Requirement 8: Special Cases Labeling

**User Story:** As a blind spot analyst, I want the five special cases clearly labeled, so that I can identify edge case scenarios requiring special handling

#### Acceptance Criteria

1. THE BSRI_Document SHALL identify five Special_Cases: static obstacles, pedestrians at speed, cyclists in zone, door opening, and reversing
2. THE BSRI_Document SHALL provide a distinct label for each of the five Special_Cases
3. THE BSRI_Document SHALL document the unique risk characteristics of each Special_Case
4. THE BSRI_Document SHALL explain how BSRI calculation or interpretation differs for each Special_Case

### Requirement 9: Consistent Worked Example

**User Story:** As a safety engineer learning BSRI, I want a consistent worked example, so that I can verify my understanding of the calculation methodology

#### Acceptance Criteria

1. THE BSRI_Document SHALL include a Worked_Example demonstrating complete BSRI calculation
2. THE Worked_Example SHALL use consistent parameter values throughout all calculation steps
3. THE Worked_Example SHALL show intermediate calculation results at each step
4. THE Worked_Example SHALL arrive at a final BSRI score consistent with the shown intermediate values
5. WHERE the V2_Document contained inconsistencies in the worked example, THE V3_Document SHALL resolve them

### Requirement 10: Sensor Source Documentation

**User Story:** As a sensor integration engineer, I want sensor sources documented in formulas, so that I understand which physical sensors contribute to each risk term

#### Acceptance Criteria

1. WHERE a formula uses a measured or detected value, THE BSRI_Document SHALL identify the sensor type providing that value
2. THE BSRI_Document SHALL document sensor sources for detection range, object classification, and velocity measurements
3. WHERE multiple sensor types can provide a value, THE BSRI_Document SHALL document all applicable sensor types
4. THE BSRI_Document SHALL distinguish between required sensors and optional sensors for each parameter

### Requirement 11: Maintain Multiplicative Formula

**User Story:** As a technical author, I want to maintain the multiplicative formula, so that existing BSRI implementations remain valid

#### Acceptance Criteria

1. THE V3_Document SHALL use the same multiplicative formula structure as the V2_Document
2. THE V3_Document SHALL NOT introduce additive, weighted average, or alternative calculation methodologies
3. WHERE formula presentation is improved for clarity, THE V3_Document SHALL maintain mathematical equivalence to the V2 formula

### Requirement 12: Create V3 as New File

**User Story:** As a document manager, I want V3 created as a new file, so that V2 remains available for reference and version comparison

#### Acceptance Criteria

1. THE V3_Document SHALL be created as a new file separate from the V2_Document
2. THE V2_Document SHALL remain unmodified in the repository
3. THE V3_Document SHALL include a version identifier clearly marking it as V3
4. THE V3_Document SHALL include a change summary documenting differences from V2

### Requirement 13: Calibration Data Status

**User Story:** As a validation engineer, I want calibration data status clearly marked, so that I understand the empirical validation level of BSRI

#### Acceptance Criteria

1. WHERE calibration data is absent, THE BSRI_Document SHALL explicitly state that calibration data is not yet available
2. WHERE calibration data is absent, THE BSRI_Document SHALL mark parameter values as "initial" or "provisional"
3. THE BSRI_Document SHALL NOT imply that calibration has been performed when it has not
4. WHERE parameters are marked as initial, THE BSRI_Document SHALL document the intended calibration methodology

### Requirement 14: Remove Unsubstantiated Claims

**User Story:** As a peer reviewer, I want unsubstantiated claims removed, so that the document contains only verifiable information

#### Acceptance Criteria

1. WHERE the V2_Document made claims without supporting evidence or citation, THE V3_Document SHALL remove those claims
2. WHERE a claim is essential but lacks substantiation, THE V3_Document SHALL mark it as a hypothesis or assumption requiring validation
3. THE V3_Document SHALL NOT include performance assertions, safety claims, or regulatory compliance statements without documented support
4. WHERE effectiveness or accuracy claims are made, THE V3_Document SHALL cite empirical data or provide theoretical justification
