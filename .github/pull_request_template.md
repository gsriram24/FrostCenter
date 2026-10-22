## Description

<!-- Briefly describe the purpose of this PR and what changes were made. -->

---

## Type of Change

- [ ] **New Laptop Model / Board Mapping** (adding `MS-XXXX` to `models/database.json` and `README.md`)
- [ ] **Bug Fix** (non-breaking change fixing an issue)
- [ ] **Feature / Enhancement** (new capability or UI improvement)
- [ ] **Documentation Update** (guides, installation instructions, README)
- [ ] **Refactoring / Performance** (code improvements with no functional change)

---

## Hardware & Environment (If Applicable)

- **MSI Laptop Model:**
- **Board Name (`MS-XXXX`):**
- **Config Group (e.g., `G1_7`, `G2_3`):**
- **Linux Distribution:**
- **Desktop Environment:**
- **Kernel Version:**

---

## Verification Checklist

- [ ] Tested on real MSI hardware, or verified using `python3 tests/simulate_frostcenter.py`
- [ ] **Zero Guessing on EC Registers:** All register addresses were cross-referenced with `msi-ec` kernel driver code, `isw`, or verified diagnostic dumps
- [ ] Python syntax validated (`python3 -m py_compile OFC.py tests/simulate_frostcenter.py ui/*.py`)
- [ ] Read-only mode safety preserved (no writes executed when `--read-only` is active)
- [ ] Documentation updated (`README.md`, `CONTRIBUTING.md`, or `models/database.json` where appropriate)
