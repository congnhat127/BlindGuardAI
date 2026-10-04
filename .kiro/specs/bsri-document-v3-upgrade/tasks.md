# Implementation Plan: BSRI V3 Documentation Upgrade

## Overview

This plan guides the upgrade of the Blind Spot Risk Index (BSRI) documentation from V2 to V3. The implementation focuses on correcting regulatory citations, adding complete parameter provenance, fixing inconsistencies, and improving clarity while maintaining the existing multiplicative formula structure. All work involves creating and editing markdown documentation files.

## Tasks

- [ ] 1. Research and audit V2 documentation
  - [ ] 1.1 Extract and catalog all parameters from V2 document
    - Create a working list of all parameter symbols used in BSRI formulas
    - Document current parameter definitions and any existing source attributions
    - Identify parameters with unclear or missing source information
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [ ] 1.2 Audit regulatory citations in V2
    - Identify all instances of ISO 15622 citations
    - List all UNECE R151, R158, and R159 citations with context
    - Document W_vru current attribution
    - Flag any citations that appear to extend beyond regulatory scope
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 4.1_
  
  - [ ] 1.3 Analyze V2 worked example for inconsistencies
    - Extract all parameter values used in worked example
    - Trace each value through all calculation steps
    - Document any inconsistencies or unclear intermediate results
    - _Requirements: 9.2, 9.4, 9.5_

- [ ] 2. Research regulatory standards and parameter sources
  - [ ] 2.1 Obtain and review UNECE regulations
    - Access UNECE R151 (BSIS - lateral blind spots)
    - Access UNECE R158 (Reversing camera/monitor)
    - Access UNECE R159 (MOIS - low-speed forward detection)
    - Extract relevant sections defining detection parameters
    - _Requirements: 3.1, 3.2, 3.3, 6.2_
  
  - [ ] 2.2 Research W_vru parameter source
    - Search UNECE regulations for VRU width specifications
    - Check ISO standards for relevant VRU definitions
    - If no regulatory source found, document engineering rationale
    - _Requirements: 4.2, 4.3_
  
  - [ ] 2.3 Identify sensor sources for parameters
    - For each measured parameter, identify providing sensor type(s)
    - Distinguish required vs. optional sensors
    - Document sensor fusion considerations
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ] 3. Create V3 document structure and framework
  - [ ] 3.1 Create BSRI_V3_Document.md with base structure
    - Set up file at 6_Docs_and_References/BSRI_V3_Document.md
    - Add document header with version identifier (V3)
    - Create section placeholders for all major sections (1-12 from design)
    - Add metadata section with version and date
    - _Requirements: 12.1, 12.3_
  
  - [ ] 3.2 Write parameter classification framework section
    - Define the three classification tiers: Standard, Vehicle, Engineering
    - Document criteria for each tier
    - Provide examples for each classification type
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 3.3 Create table templates
    - Design provenance table schema
    - Design sensor sources table schema
    - Design references table schema
    - _Requirements: 6.1, 6.4, 7.1, 10.1_

- [ ] 4. Checkpoint - Verify structure and framework
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Write corrected parameter definitions
  - [ ] 5.1 Classify all parameters into tiers
    - For each parameter from audit, assign classification (Standard/Vehicle/Engineering)
    - Ensure each parameter has exactly one classification
    - Document rationale for Engineering parameters
    - _Requirements: 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 5.2 Remove ISO 15622 from blind spot contexts
    - For each ISO 15622 citation identified in audit, remove or replace
    - Substitute correct regulatory source where applicable
    - Reclassify as Engineering parameter if no regulatory source exists
    - Retain ISO 15622 only if explicit ACC context exists
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ] 5.3 Write corrected W_vru definition
    - Remove incorrect ISO 15622 attribution from W_vru
    - Add correct regulatory source with section reference if found
    - If no regulatory source, classify as Engineering with documented rationale
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 5.4 Write parameter definitions organized by tier
    - For Standard parameters: cite regulatory source with section reference
    - For Vehicle parameters: reference vehicle specification sources
    - For Engineering parameters: document calculation method or design assumption
    - Include symbol, name, description, unit, sensor type for each parameter
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 6.2, 10.1, 10.2_

- [ ] 6. Write regulatory standards section
  - [ ] 6.1 Write UNECE R151 section (BSIS)
    - Scope: Lateral blind spot detection for vehicles alongside
    - Document applicable parameters and section references
    - Explicitly limit scope to lateral blind spots only
    - _Requirements: 3.1, 3.4_
  
  - [ ] 6.2 Write UNECE R158 section (Reversing)
    - Scope: Reversing camera/monitor requirements
    - Document applicable parameters and section references
    - Explicitly limit scope to reversing scenarios only
    - _Requirements: 3.2, 3.4_
  
  - [ ] 6.3 Write UNECE R159 section (MOIS)
    - Scope: Moving Off Information System (low-speed forward detection)
    - Document applicable parameters and section references
    - Explicitly limit scope to low-speed forward detection only
    - _Requirements: 3.3, 3.4_
  
  - [ ] 6.4 Write ISO 15622 section (if needed)
    - Include only if explicit ACC context exists in BSRI
    - Clearly mark as ACC-specific, not blind spot related
    - _Requirements: 2.3_

- [ ] 7. Write geometric parameters section with symmetry
  - [ ] 7.1 Write SWEPT_PATH_RIGHT definition
    - Document geometric principles for right turn swept path
    - Provide formula with vehicle geometry parameters
    - Include diagram showing swept path geometry
    - Provide calculation example
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ] 7.2 Write SWEPT_PATH_LEFT definition with symmetry
    - Use identical geometric principles as SWEPT_PATH_RIGHT
    - Provide mirrored formula with equivalent detail level
    - Include mirrored diagram (reflected coordinate system)
    - Provide calculation example with same detail as RIGHT
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 8. Document special cases
  - [ ] 8.1 Write special case framework
    - Introduce the five special cases requiring distinct handling
    - Define the structure for each case documentation
    - _Requirements: 8.1, 8.2_
  
  - [ ] 8.2 Document SC1: Static obstacles
    - Provide distinct label and description
    - Document unique risk characteristics
    - Explain how BSRI calculation or interpretation differs
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ] 8.3 Document SC2: Pedestrians at speed
    - Provide distinct label and description
    - Document unique risk characteristics (VRU velocity considerations)
    - Explain how BSRI calculation or interpretation differs
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ] 8.4 Document SC3: Cyclists in zone
    - Provide distinct label and description
    - Document unique risk characteristics (lateral motion in blind spot)
    - Explain how BSRI calculation or interpretation differs
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ] 8.5 Document SC4: Door opening
    - Provide distinct label and description
    - Document unique risk characteristics (quasi-static vehicle boundary expansion)
    - Explain how BSRI calculation or interpretation differs
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ] 8.6 Document SC5: Reversing
    - Provide distinct label and description
    - Document unique risk characteristics (rear-facing sensor coverage)
    - Explain how BSRI calculation or interpretation differs
    - _Requirements: 8.2, 8.3, 8.4_

- [ ] 9. Checkpoint - Verify parameter definitions and special cases
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Create worked example with mathematical consistency
  - [ ] 10.1 Select consistent parameter values
    - Choose realistic vehicle parameters for example
    - Choose realistic scenario parameters
    - Document all values in single "Given" section at start
    - Include units for all values
    - _Requirements: 9.1, 9.2_
  
  - [ ] 10.2 Write step-by-step calculation
    - Break BSRI calculation into discrete steps
    - For each step: show formula, substitute values, compute result
    - Show all intermediate results with units
    - Reference the "Given" values consistently throughout
    - _Requirements: 9.2, 9.3_
  
  - [ ] 10.3 Compute and verify final BSRI score
    - Calculate final BSRI score from intermediate results
    - Verify result is consistent with multiplicative formula
    - Verify all intermediate values correctly used
    - _Requirements: 9.4, 9.5_

- [ ] 11. Create provenance and reference tables
  - [ ] 11.1 Create complete parameter provenance table
    - List every parameter used in BSRI calculations
    - For each parameter: symbol, description, classification tier, source, section reference
    - For Engineering parameters: include rationale or design assumption
    - Cross-check against parameter definitions section for completeness
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ] 11.2 Create sensor sources table
    - Map each measured parameter to sensor type(s)
    - Mark sensors as required or optional
    - Document sensor fusion considerations
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 11.3 Create references section
    - List all cited standards (UNECE R151, R158, R159, ISO 15622 if applicable)
    - Include full title for each standard
    - Include publication date or version for each standard
    - Verify every citation in document has corresponding reference entry
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 12. Write calibration status and transparency sections
  - [ ] 12.1 Write calibration status section
    - Explicitly state that calibration data is not yet available
    - Mark parameter values as "Initial (not calibrated)" or "Provisional"
    - Do not imply calibration has been performed
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [ ] 12.2 Document intended calibration methodology
    - Describe planned calibration approach
    - Identify required empirical data sources
    - Explain validation methodology (correlation with collision data)
    - _Requirements: 13.4_

- [ ] 13. Review and remove unsubstantiated claims
  - [ ] 13.1 Audit document for unsubstantiated claims
    - Search for performance assertions without data
    - Search for safety effectiveness claims without evidence
    - Search for regulatory compliance statements without verification
    - Search for accuracy claims without testing
    - _Requirements: 14.1, 14.3_
  
  - [ ] 13.2 Remove or mark unsubstantiated content
    - Remove non-essential unsubstantiated claims
    - Mark essential but unsubstantiated claims as "Hypothesis requiring validation"
    - Reframe theoretical claims with appropriate qualifiers
    - Ensure no false performance or safety claims remain
    - _Requirements: 14.1, 14.2, 14.4_

- [ ] 14. Verify formula preservation and mathematical equivalence
  - [ ] 14.1 Verify multiplicative formula structure maintained
    - Confirm V3 uses same multiplicative formula structure as V2
    - Ensure no additive or weighted average methodologies introduced
    - Document any presentation improvements for clarity
    - Verify mathematical equivalence to V2 formula
    - _Requirements: 11.1, 11.2, 11.3_

- [ ] 15. Create change summary document
  - [ ] 15.1 Create BSRI_V3_Change_Summary.md
    - Create file at 6_Docs_and_References/BSRI_V3_Change_Summary.md
    - Document purpose and scope of V3 upgrade
    - _Requirements: 12.4_
  
  - [ ] 15.2 Document all major corrections
    - List ISO 15622 removal instances with before/after
    - Document W_vru attribution correction
    - Document SWEPT_PATH_LEFT addition
    - List worked example inconsistency corrections
    - Document provenance table addition
    - List any unsubstantiated claims removed
    - _Requirements: 12.4_

- [ ] 16. Final validation and quality checks
  - [ ] 16.1 Run structural validation checklist
    - Verify all required sections present (sections 1-12 from design)
    - Verify section ordering is logical
    - Verify all cross-references resolve correctly
    - Verify table of contents matches structure
    - _Requirements: All_
  
  - [ ] 16.2 Run content validation checklist
    - Verify every parameter classified exactly once
    - Verify every parameter appears in provenance table
    - Verify every citation appears in references section
    - Verify worked example is mathematically consistent
    - _Requirements: 1.2, 6.1, 7.4, 9.2, 9.4_
  
  - [ ] 16.3 Run citation validation checklist
    - Confirm ISO 15622 removed from blind spot contexts
    - Confirm UNECE R151 limited to lateral blind spots
    - Confirm UNECE R158 limited to reversing
    - Confirm UNECE R159 limited to MOIS
    - Confirm W_vru correctly attributed
    - _Requirements: 2.1, 3.1, 3.2, 3.3, 4.2_
  
  - [ ] 16.4 Run symmetry validation checklist
    - Verify SWEPT_PATH_LEFT has same structure as RIGHT
    - Verify SWEPT_PATH_LEFT has same detail level as RIGHT
    - Verify SWEPT_PATH_LEFT has equivalent formulas/diagrams
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ] 16.5 Run completeness validation checklist
    - Verify all five special cases labeled and described
    - Verify provenance table lists all parameters
    - Verify references section complete
    - Verify sensor sources documented for all measured values
    - _Requirements: 6.1, 7.1, 8.1, 10.1_
  
  - [ ] 16.6 Run transparency validation checklist
    - Verify calibration absence explicitly stated
    - Verify provisional parameters marked
    - Verify no false calibration claims
    - Verify unsubstantiated claims removed or marked
    - _Requirements: 13.1, 13.2, 13.3, 14.1_

- [ ] 17. Final checkpoint - Complete documentation review
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This is a documentation project; all tasks involve creating or editing markdown files
- V2 document (BSRI_V2_Document.md) must remain unmodified throughout this process
- Research tasks (2.1, 2.2) may require access to regulatory standards that could be behind paywalls
- If regulatory standards cannot be accessed, document this limitation and classify affected parameters as "pending verification"
- The multiplicative formula structure must be preserved (Requirement 11); only presentation and citations are being corrected
- All parameter attributions must be verifiable; when in doubt, classify as Engineering with documented rationale
- Worked example mathematical consistency is critical; verify all calculations before finalizing
- Quality validation tasks (16.1-16.6) serve as final verification before completion

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3"] },
    { "id": 3, "tasks": ["5.1", "5.2", "5.3"] },
    { "id": 4, "tasks": ["5.4", "6.1", "6.2", "6.3", "6.4"] },
    { "id": 5, "tasks": ["7.1"] },
    { "id": 6, "tasks": ["7.2", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4", "8.5", "8.6"] },
    { "id": 8, "tasks": ["10.1"] },
    { "id": 9, "tasks": ["10.2"] },
    { "id": 10, "tasks": ["10.3", "11.1", "11.2", "11.3"] },
    { "id": 11, "tasks": ["12.1", "12.2", "13.1"] },
    { "id": 12, "tasks": ["13.2", "14.1"] },
    { "id": 13, "tasks": ["15.1"] },
    { "id": 14, "tasks": ["15.2"] },
    { "id": 15, "tasks": ["16.1", "16.2", "16.3", "16.4", "16.5", "16.6"] }
  ]
}
```
