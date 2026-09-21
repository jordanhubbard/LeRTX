# Verified native wheel packaging

### Requirement: Offline exact-target dependency closure

Declare direct runtime requirements in `source/requirements.txt` and the complete
transitive wheel closure in adjacent `source/python-wheel-lock.json`, using
`literate-ai/python-wheel-lock@1`. Bind the actual selected interpreter's marker
environment and compatible tags, exact filenames, SHA-256 hashes, Python version
constraints and dependency metadata. Do not fabricate hashes or reuse a lock for
a different OS or interpreter. Use the exact package versions in desktop-python.

The operator provisions an exact private wheelhouse before admission. Application
code must never acquire or install its own dependencies. The lifecycle stages
verified wheel bytes, installs offline without dependency resolution or build
scripts, and independently verifies installed payloads and import ownership.
Missing wheels, inconsistent metadata, target mismatch, or modified payloads fail
closed. Do not select a competing Make or other build-system command profile.

For Linux USD 25.11, use only the separately hashed metadata-repaired archive
produced by the reviewed repair process. Preserve the original archive and repair
provenance outside the active wheelhouse. The repaired archive must pass the
unchanged strict validator; its hash must be the lock's artifact hash. The Windows
USD archive remains unmodified. Never place both variants in one wheelhouse.

The application tree export includes source, sealed runtime evidence and the
verified retained dependency payload managed by the lifecycle. Never describe
portable configuration tests as native desktop acceptance.

#### Scenario: Exact native closure is available

- **WHEN** all locked wheel bytes match the selected interpreter and strict metadata checks
- **THEN** the offline lifecycle may construct and independently verify the runtime
- **AND** execution remains subject to application acceptance and authorization

#### Scenario: Closure or target differs

- **WHEN** a wheel, hash, metadata edge, installed payload or target identity differs
- **THEN** admission fails without network fallback or relaxed validation
