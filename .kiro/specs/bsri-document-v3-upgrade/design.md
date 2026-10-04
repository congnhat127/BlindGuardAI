# Design Document: BSRI V3 Documentation Upgrade

## Overview

This design specifies the structure, content organization, and authoring approach for upgrading the Blind Spot Risk Index (BSRI) documentation from V2 to V3. The upgrade addresses technical accuracy issues, regulatory standard misattributions, missing provenance information, and inconsistencies while maintaining the existing multiplicative formula.

### Design Principles

1. **Accuracy First**: Every parameter attribution and regulatory citation must be verifiable
2. **Traceability**: Every parameter must be traceable to its authoritative source
3. **Clarity Through Structure**: Organize content by classification tier to reveal parameter relationships
4. **Mathematical Consistency**: Maintain formula equivalence while improving presentation
5. **Transparency**: Explicitly mark provisional values and untested claims

## Architecture

### Document Structure

The V3 document will be organized into the following major sections:

```
1. Introduction
   - Purpose and scope
   - Version history and change summary
   - Relationship to V2

2. Parameter Classification Framework
   - Standard Parameters (regulatory-derived)
   - Vehicle Parameters (model-specific)
   - Engineering Parameters (calculated/designed)

3. BSRI Calculation Methodology
   - Multiplicative formula specification
   - Mathematical notation and conventions
   - Calculation workflow

4. Parameter Definitions and Sources
   - Organized by classification tier
   - Each parameter with: symbol, description, source, sensor mapping
   
5. Regulatory Standards and Scope
   - UNECE R151 (BSIS - lateral blind spots)
   - UNECE R158 (Reversing camera/monitor)
   - UNECE R159 (MOIS - low-speed forward)
   - ISO 15622 (ACC - correct context only)

6. Geometric Parameters
   - SWEPT_PATH_LEFT definition (symmetrical to RIGHT)
   - SWEPT_PATH_RIGHT definition
   - Turning geometry calculations

7. Special Cases
   - SC1: Static obstacles
   - SC2: Pedestrians at speed
   - SC3: Cyclists in zone
   - SC4: Door opening
   - SC5: Reversing

8. Worked Example
   - Complete calculation with consistent parameters
   - Step-by-step intermediate results
   - Final BSRI score computation

9. Sensor Sources Table
   - Mapping parameters to physical sensors
   - Required vs. optional sensors
   - Sensor fusion considerations

10. Parameter Provenance Table
    - Complete parameter listing
    - Source attribution for each parameter
    - Classification tier for each parameter

11. Calibration Status
    - Current calibration state (absent)
    - Provisional parameter markers
    - Intended calibration methodology

12. References
    - Full standard titles
    - Publication dates/versions
    - Section-specific citations
```

### Component Descriptions

#### 1. Parameter Classification System

A three-tier taxonomy that organizes all BSRI parameters:

**Standard Parameters**: Values mandated or defined by regulatory standards
- Source: Specific sections of UNECE regulations or ISO standards
- Example: Minimum detection ranges from UNECE R151
- Characteristic: Fixed by regulation, not vehicle-specific

**Vehicle Parameters**: Values specific to individual vehicle models
- Source: Vehicle specifications, technical datasheets, or measurements
- Example: Vehicle width, wheelbase, sensor mounting positions
- Characteristic: Varies by vehicle model

**Engineering Parameters**: Values derived from calculations or design decisions
- Source: Engineering analysis, safety margins, or theoretical models
- Example: Risk weighting factors, threshold values
- Characteristic: Requires documented rationale

#### 2. Regulatory Citation Correction Module

This component ensures accurate regulatory scoping:

**ISO 15622 Removal**: Systematically remove ISO 15622 citations from blind spot contexts
- Audit all parameter definitions for incorrect ISO 15622 references
- Substitute correct regulatory source or reclassify as Engineering parameter
- Retain ISO 15622 only for explicit ACC contexts (if any exist)

**UNECE Scope Enforcement**:
- R151: Strictly lateral blind spot detection (vehicles alongside)
- R158: Strictly reversing camera/monitor requirements
- R159: Strictly MOIS low-speed forward detection
- No scope extensions beyond regulatory domains

**W_vru Attribution Correction**:
- Remove incorrect ISO 15622 attribution
- Research correct regulatory source with section reference
- If no regulatory source exists, classify as Engineering parameter with rationale

#### 3. Geometric Symmetry Module

Ensures left/right turning calculations are mathematically consistent:

**SWEPT_PATH_LEFT Definition**:
- Use identical geometric principles as SWEPT_PATH_RIGHT
- Provide equivalent formulas (mirror the geometry)
- Include equivalent diagrams (reflected coordinate system)
- Provide equivalent worked examples

**Implementation Approach**:
```
SWEPT_PATH_RIGHT: Given turning radius R_turn and vehicle geometry
  SP_RIGHT = f(R_turn, vehicle_width, wheelbase, ...)

SWEPT_PATH_LEFT: Mirror the geometry
  SP_LEFT = f(R_turn, vehicle_width, wheelbase, ...)
  (Same function, coordinate system reflected)
```

#### 4. Provenance Table Generator

Creates comprehensive parameter traceability:

**Table Schema**:
```
| Parameter Symbol | Description | Classification | Source | Section Reference |
|------------------|-------------|----------------|--------|-------------------|
| w_veh            | Vehicle width | Vehicle | Vehicle spec | Manufacturer datasheet |
| R_detection      | Detection range | Standard | UNECE R151 | Section 5.6.4.1 |
| k_risk           | Risk factor | Engineering | Safety margin analysis | Design assumption |
```

**Population Strategy**:
1. Extract all parameters from BSRI formula
2. For each parameter, identify authoritative source
3. Classify parameter (Standard/Vehicle/Engineering)
4. Document rationale for Engineering parameters
5. Cross-reference with formula usage

#### 5. Special Cases Framework

Provides distinct labeling and handling for edge scenarios:

**Case Structure** (for each of five cases):
```
SC{n}: {Case Name}
  Description: What makes this scenario unique
  Risk Characteristics: Why standard calculation may not apply
  BSRI Modification: How calculation or interpretation differs
  Detection Challenges: Sensor limitations in this scenario
  Example: Concrete instance of this case
```

**Five Cases**:
- SC1: Static obstacles (detection vs. tracking differences)
- SC2: Pedestrians at speed (VRU velocity considerations)
- SC3: Cyclists in zone (lateral motion in blind spot)
- SC4: Door opening (quasi-static expansion of vehicle boundary)
- SC5: Reversing (rear-facing sensor coverage)

#### 6. Worked Example Consistency Module

Ensures mathematical correctness throughout calculation:

**Consistency Enforcement**:
1. Define parameter values at start (single source of truth)
2. Reference these values consistently in all steps
3. Show all intermediate calculations explicitly
4. Verify final result = f(intermediate results)
5. Include units throughout

**Example Structure**:
```python
# Given vehicle and scenario parameters
vehicle_width = 2.0  # m
detection_range = 3.5  # m
velocity = 15.0  # m/s
...

# Step 1: Calculate geometric risk
R_geometric = f(vehicle_width, detection_range)
R_geometric = 2.0 / 3.5 = 0.571

# Step 2: Calculate velocity risk
R_velocity = g(velocity, threshold)
R_velocity = 15.0 / 20.0 = 0.750

# Step 3: Combined BSRI (multiplicative)
BSRI = R_geometric × R_velocity × ...
BSRI = 0.571 × 0.750 × ... = X.XXX
```

#### 7. Sensor Source Documentation

Maps each parameter to physical sensors:

**Sensor Mapping Table**:
```
| Parameter | Sensor Type(s) | Required/Optional | Fusion Notes |
|-----------|----------------|-------------------|--------------|
| Object distance | Radar, Ultrasonic, Camera | Radar (required) | Fusion improves accuracy |
| Object classification | Camera | Required | Deep learning |
| Relative velocity | Radar, Camera | Radar (required) | Doppler or tracking |
```

**Documentation Requirements**:
- Identify sensor type for each measured value in formulas
- Specify which sensors are mandatory vs. enhancement
- Document multi-sensor fusion strategies where applicable

#### 8. Calibration Status Module

Transparently communicates validation state:

**Status Markers**:
- Parameter values marked as "Initial (not calibrated)"
- Explicit statement: "Calibration data not yet available"
- No implied or stated calibration without evidence

**Intended Calibration Section**:
- Describe planned calibration methodology
- Identify required empirical data sources
- Explain validation approach (e.g., correlation with collision data)

#### 9. Claims Removal Module

Ensures only substantiated content remains:

**Audit Categories**:
1. Performance claims without data → Remove or mark as hypothesis
2. Safety effectiveness without evidence → Remove or mark as assumption
3. Regulatory compliance without verification → Remove or mark as intended
4. Accuracy claims without testing → Remove or mark as theoretical

**Remediation Strategy**:
- Essential but unsubstantiated → Mark as "Hypothesis requiring validation"
- Non-essential and unsubstantiated → Remove entirely
- Theoretical basis exists → Reframe as "Theoretically expected to..." with justification

## Data Models

### Parameter Definition Model

```python
class ParameterDefinition:
    """Represents a single BSRI parameter"""
    symbol: str                    # e.g., "w_veh", "R_detection"
    name: str                      # Human-readable name
    description: str               # What this parameter represents
    classification: str            # "Standard", "Vehicle", or "Engineering"
    unit: str                      # Physical unit (m, m/s, dimensionless)
    source: str                    # Authoritative source
    source_section: Optional[str]  # Section/clause reference
    sensor_type: Optional[List[str]]  # Sensors providing this value
    is_calibrated: bool            # Calibration status
    rationale: Optional[str]       # For Engineering parameters
```

### Special Case Model

```python
class SpecialCase:
    """Represents one of five BSRI edge cases"""
    case_id: str                   # "SC1" through "SC5"
    name: str                      # e.g., "Static Obstacles"
    description: str               # What makes this case special
    risk_characteristics: str      # Unique risk factors
    bsri_modification: str         # How calculation differs
    detection_challenges: str      # Sensor limitations
    example_scenario: str          # Concrete instance
```

### Worked Example Model

```python
class WorkedExample:
    """Represents the complete worked example calculation"""
    vehicle_params: Dict[str, float]    # Input vehicle parameters
    scenario_params: Dict[str, float]   # Input scenario parameters
    calculation_steps: List[CalculationStep]  # Ordered steps
    final_bsri_score: float            # Final result
    
class CalculationStep:
    step_number: int
    description: str                    # What this step computes
    formula: str                        # Mathematical expression
    substituted_values: str             # Formula with numbers
    result: float                       # Computed value
    unit: str                          # Result unit
```

## Components and Interfaces

### Component Integration Overview

The components described in the Architecture section work together to produce the V3 documentation. Each component contributes specific content sections, and their outputs are integrated into the final document structure.

**Component Dependencies**:
- Parameter Classification System → feeds → Provenance Table Generator
- Regulatory Citation Correction Module → validates → Parameter Classification System
- Geometric Symmetry Module → provides content for → Parameter Definitions section
- Special Cases Framework → standalone section in final document
- Worked Example Consistency Module → validates → Parameter Definitions
- Sensor Source Documentation → cross-references → Parameter Definitions
- Calibration Status Module → adds metadata to → Parameter Definitions
- Claims Removal Module → audits → all content sections

### Document Generation Interface

Since this is a documentation project, the primary "interface" is the document structure and authoring guidelines:

**Section Template**:
```markdown
## {Section Title}

### Purpose
{Why this section exists}

### Content Requirements
- [ ] Required element 1
- [ ] Required element 2
- [ ] ...

### Quality Criteria
- Accuracy: {How accuracy is ensured}
- Completeness: {What constitutes complete}
- Traceability: {How sources are cited}

### Cross-References
- Related sections: {Links}
- Referenced standards: {Citations}
```

**Parameter Definition Template**:
```markdown
#### {Parameter Symbol}: {Parameter Name}

**Classification**: {Standard | Vehicle | Engineering}

**Description**: {What this parameter represents}

**Source**: {Authoritative source with section reference}

**Unit**: {Physical unit}

**Sensor**: {Sensor type(s) providing this value}

**Calibration Status**: {Calibrated | Initial (not calibrated)}

**Rationale**: {For Engineering parameters, explain derivation}
```

## Error Handling

### Documentation Error Types

Since this is documentation (not executable code), "errors" are content issues:

**Type 1: Citation Errors**
- **Detection**: Manual review + automated search for incorrect standard references
- **Handling**: Correct citation or reclassify parameter
- **Example**: ISO 15622 cited for blind spot → Remove or replace with correct standard

**Type 2: Inconsistency Errors**
- **Detection**: Cross-referencing worked example values
- **Handling**: Recalculate with consistent parameters
- **Example**: Worked example uses different vehicle width in different steps

**Type 3: Completeness Errors**
- **Detection**: Checklist verification against requirements
- **Handling**: Add missing content
- **Example**: Provenance table missing a parameter used in formula

**Type 4: Scope Errors**
- **Detection**: Regulatory standard domain review
- **Handling**: Limit citation to applicable domain
- **Example**: UNECE R151 extended beyond lateral blind spots

**Type 5: Unsubstantiated Claims**
- **Detection**: Review for evidence/citation
- **Handling**: Remove, mark as hypothesis, or provide justification
- **Example**: "BSRI accurately predicts collision risk" without calibration data

## Testing Strategy

Since this project produces documentation rather than executable code, traditional software testing does not apply. However, we define validation approaches:

### Document Validation Checklist

**Structural Validation**:
- [ ] All required sections present (per Requirements 1-14)
- [ ] Section ordering logical and consistent
- [ ] Cross-references resolve correctly
- [ ] Table of contents matches actual structure

**Content Validation**:
- [ ] Every parameter classified exactly once (Standard/Vehicle/Engineering)
- [ ] Every parameter appears in Provenance Table
- [ ] Every citation appears in References section
- [ ] Worked example mathematically consistent

**Citation Validation**:
- [ ] ISO 15622 removed from blind spot contexts (Req 2.1)
- [ ] UNECE R151 limited to lateral blind spots (Req 3.1)
- [ ] UNECE R158 limited to reversing (Req 3.2)
- [ ] UNECE R159 limited to MOIS (Req 3.3)
- [ ] W_vru correctly attributed (Req 4)

**Symmetry Validation**:
- [ ] SWEPT_PATH_LEFT has same structure as SWEPT_PATH_RIGHT (Req 5.1)
- [ ] SWEPT_PATH_LEFT has same detail level as SWEPT_PATH_RIGHT (Req 5.2)
- [ ] SWEPT_PATH_LEFT has equivalent formulas/diagrams (Req 5.3)

**Completeness Validation**:
- [ ] All five Special Cases labeled and described (Req 8)
- [ ] Provenance Table lists all parameters (Req 6.1)
- [ ] References section complete (Req 7)
- [ ] Sensor sources documented for all measured values (Req 10)

**Transparency Validation**:
- [ ] Calibration absence explicitly stated (Req 13.1)
- [ ] Provisional parameters marked (Req 13.2)
- [ ] No false calibration claims (Req 13.3)
- [ ] Unsubstantiated claims removed or marked (Req 14)

**Mathematical Validation**:
- [ ] Multiplicative formula preserved (Req 11.1)
- [ ] No alternative methodologies introduced (Req 11.2)
- [ ] Mathematical equivalence to V2 maintained (Req 11.3)
- [ ] Worked example internally consistent (Req 9.2, 9.4)

### Review Protocol

**Stage 1: Self-Review**
- Author reviews against validation checklist
- Verify all requirements addressed
- Check mathematical calculations in worked example

**Stage 2: Technical Review**
- Domain expert reviews parameter attributions
- Verify regulatory citations against actual standards
- Validate geometric calculations

**Stage 3: Editorial Review**
- Check clarity and consistency of presentation
- Verify formatting and structure
- Ensure terminology consistency

**Stage 4: Compliance Review**
- Verify no unsubstantiated claims remain
- Confirm calibration status accurately represented
- Validate reference completeness

## File Organization

### Repository Structure

```
6_Docs_and_References/
├── BSRI_V2_Document.md          # Original V2 (preserved, unmodified)
├── BSRI_V3_Document.md          # New V3 document
├── BSRI_V3_Change_Summary.md    # Detailed change log V2→V3
└── regulatory_standards/         # Reference copies of standards (if permitted)
    ├── UNECE_R151_summary.md
    ├── UNECE_R158_summary.md
    └── UNECE_R159_summary.md
```

### Version Control Strategy

**V2 Preservation** (Requirement 12.2):
- V2 file remains in repository unchanged
- No modifications to V2_Document.md
- V2 serves as reference for comparison

**V3 Creation** (Requirement 12.1):
- Create BSRI_V3_Document.md as new file
- Include "Version 3" identifier in header (Requirement 12.3)
- Add version metadata section

**Change Tracking** (Requirement 12.4):
- Create separate change summary document
- Document each major correction (ISO 15622, W_vru, etc.)
- Provide before/after for key changes

## Implementation Notes

### Authoring Tools

**Markdown**: Primary format for documentation
- **Rationale**: Version control friendly, widely supported
- **Extensions**: Tables, math notation (LaTeX/MathJax), diagrams (Mermaid)

**Diagram Tools**:
- **Geometric diagrams**: Vector graphics (SVG) or ASCII art
- **Flowcharts**: Mermaid syntax embedded in markdown
- **Formulas**: LaTeX math notation

### Research Requirements

To complete V3 accurately, the following research is required:

**Regulatory Standard Access**:
- Obtain UNECE R151, R158, R159 full text
- Identify specific sections for parameter definitions
- Document exact regulatory language

**W_vru Source Investigation**:
- Search UNECE regulations for VRU width specifications
- Check ISO standards for relevant definitions
- If no regulatory source, document engineering rationale

**V2 Audit**:
- Extract all current parameter definitions from V2
- Identify all current regulatory citations
- Document all inconsistencies in worked example

### Writing Guidelines

**Precision**:
- Use exact terminology from regulatory standards
- Include section numbers for all citations
- Specify units for all numerical values

**Clarity**:
- Define abbreviations on first use
- Use consistent notation throughout
- Provide examples for complex concepts

**Traceability**:
- Every parameter has documented source
- Every claim has citation or rationale
- Cross-references use section numbers

**Honesty**:
- Explicitly state what is not known
- Mark provisional values clearly
- No overstatement of validation status

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Analysis Note

This specification describes a documentation upgrade project rather than software development. The requirements define document content, structure, and accuracy rather than code behavior. Traditional property-based testing (which tests code behavior across many generated inputs) does not apply to documentation content validation.

Documentation validation is performed through:
- **Structural checks**: Verifying required sections and organizational elements are present
- **Consistency checks**: Ensuring worked examples are mathematically correct and parameter usage is consistent
- **Citation checks**: Verifying regulatory references are accurate and appropriately scoped
- **Completeness checks**: Confirming all parameters have provenance and all special cases are documented

These are one-time verification activities performed during document review, not properties that can be tested across a range of inputs with universal quantification.

**Therefore, no correctness properties are defined for this specification.**

If future work implements software tools to parse, validate, or generate BSRI calculations based on this documentation, those tools would have testable properties. For example:
- *For any* valid BSRI parameter set, the calculation should produce a result consistent with the documented formula
- *For any* parameter, the provenance lookup should return exactly one classification tier
- *For any* geometric configuration, SWEPT_PATH_LEFT and SWEPT_PATH_RIGHT should exhibit symmetry

However, such tools are not part of the current specification, which focuses solely on creating accurate documentation.

## Dependencies

### External Dependencies

**Regulatory Standard Documents**:
- UNECE Regulation No. 151 (BSIS)
- UNECE Regulation No. 158 (Reversing camera/monitor)
- UNECE Regulation No. 159 (MOIS)
- ISO 15622 (ACC) - for reference only

**Access Requirements**:
- May require purchase or institutional access
- Some standards available free from UNECE website
- ISO standards typically require purchase

### Internal Dependencies

**V2 Document**:
- Current BSRI_V2_Document.md must be accessible
- Required for extracting current formula
- Required for identifying specific errors to correct

**Vehicle Specifications**:
- Example vehicle parameters for worked example
- Typical sensor specifications for sensor source table
- Representative geometric values

**Domain Expertise**:
- Automotive safety engineering knowledge
- Regulatory compliance understanding
- Geometric analysis capability

## Deployment

### Document Publication

**Internal Review**:
1. Complete V3 draft
2. Conduct validation checklist review
3. Technical review by domain experts
4. Revise based on feedback

**Repository Commit**:
1. Add BSRI_V3_Document.md to repository
2. Add BSRI_V3_Change_Summary.md
3. Commit with descriptive message: "Add BSRI V3 documentation with corrected citations and complete provenance"
4. Create git tag: `bsri-v3.0`

**Communication**:
1. Notify stakeholders of V3 availability
2. Provide change summary highlighting key corrections
3. Mark V2 as deprecated (but preserved for reference)

**Documentation Integration**:
1. Update main README to reference V3 as current version
2. Update any implementation guides that reference BSRI parameters
3. Notify implementation teams of any clarifications that affect code

### Maintenance

**Future Updates**:
- When calibration data becomes available, update calibration status section
- When new regulatory standards are published, review for applicability
- When vehicle implementations reveal parameter issues, revise accordingly

**Version Control**:
- Use semantic versioning: V3.0, V3.1 (minor corrections), V4.0 (major changes)
- Maintain change log for all versions
- Preserve previous versions for traceability

## Assumptions and Constraints

### Assumptions

1. **V2 Availability**: The current V2 document is accessible and can be analyzed
2. **Standard Access**: Required regulatory standards can be obtained for accurate citation
3. **Formula Correctness**: The V2 multiplicative formula structure is fundamentally sound (only citations and consistency need correction)
4. **No Code Changes**: This upgrade only affects documentation; implementation code is not modified
5. **Single Author**: One technical author with domain knowledge performs the upgrade
6. **Review Access**: Domain experts are available for technical review

### Constraints

1. **Formula Preservation** (Requirement 11): Cannot change multiplicative structure
2. **V2 Preservation** (Requirement 12.2): Cannot modify original V2 document
3. **Citation Accuracy**: Cannot cite standards beyond their defined scope
4. **No False Claims**: Cannot claim calibration, testing, or validation that hasn't occurred
5. **Completeness**: Must document every parameter (cannot omit parameters lacking clear sources)
6. **Resource Constraint**: Standard documents may require purchase or access fees

### Risks

**Risk 1: Standard Access**
- **Issue**: Required regulatory standards may be costly or difficult to obtain
- **Mitigation**: Start with freely available UNECE regulations; document any inaccessible sources
- **Fallback**: Mark parameters as "pending verification" if standards cannot be accessed

**Risk 2: Parameter Source Uncertainty**
- **Issue**: Some parameters may not have clear regulatory sources
- **Mitigation**: Classify as Engineering parameters with documented rationale
- **Impact**: Reduces "Standard" parameter count but maintains traceability

**Risk 3: V2 Formula Ambiguity**
- **Issue**: V2 formula may be unclear or inconsistent
- **Mitigation**: Document ambiguity explicitly; propose interpretation with rationale
- **Impact**: May require stakeholder discussion to resolve

**Risk 4: Worked Example Complexity**
- **Issue**: Creating mathematically consistent worked example may reveal formula issues
- **Mitigation**: Start worked example early; surface issues for stakeholder discussion
- **Impact**: May require formula clarification (not change to structure, but to parameter definitions)

## Success Criteria

The V3 documentation upgrade is successful when:

1. ✅ All 14 requirements fully satisfied
2. ✅ Complete validation checklist passed
3. ✅ Technical review approved by domain expert
4. ✅ Zero incorrect regulatory citations remain
5. ✅ Every parameter traceable to source
6. ✅ Worked example mathematically consistent
7. ✅ V2 preserved unmodified in repository
8. ✅ Change summary documents all major corrections
9. ✅ No unsubstantiated claims present
10. ✅ Calibration status transparently communicated

## Timeline Estimate

**Phase 1: Research and Audit** (Estimated: 8-12 hours)
- Obtain regulatory standard documents
- Audit V2 for all issues mentioned in requirements
- Extract current parameter list and citations

**Phase 2: Framework Creation** (Estimated: 4-6 hours)
- Create document structure/outline
- Design parameter classification system
- Create table templates

**Phase 3: Content Development** (Estimated: 16-24 hours)
- Write parameter definitions with correct sources
- Develop provenance table
- Create symmetric geometric definitions
- Document special cases
- Write sensor source mappings

**Phase 4: Worked Example** (Estimated: 6-8 hours)
- Select consistent parameter values
- Perform step-by-step calculation
- Verify mathematical consistency
- Create clear presentation

**Phase 5: Review and Revision** (Estimated: 8-12 hours)
- Self-review against validation checklist
- Technical review incorporation
- Final consistency checks
- Change summary creation

**Total Estimated Effort**: 42-62 hours (approximately 1-1.5 weeks full-time)

---

*This design document specifies the architecture and approach for creating BSRI V3 documentation that addresses all identified issues in V2 while maintaining mathematical equivalence and improving clarity, accuracy, and traceability.*
