# Contributing to FrostCenter

Thank you for helping improve FrostCenter for the MSI Linux community! Whether you are verifying a laptop, reporting an unmapped model, or submitting code improvements, your contributions are welcome.

---

## 1. Verifying a Working Laptop

If FrostCenter works on your MSI laptop model:

### Option A: Via the App (1-Click)
1. Launch FrostCenter on your laptop.
2. If your model is not yet marked verified, click **⚡ Verify Device** at the bottom of the sidebar (or go to **Settings > Device Verification & Community > ✓ Confirm on GitHub**).
3. A pre-filled issue report will open in your browser containing your detected hardware specs, OS, kernel, and confirmed functionality checkboxes. Click **Submit new issue**.

### Option B: Propose a Pull Request Directly
You can add your laptop directly to the database and **Tested On** table:
1. In `README.md`, add your device to the table under `## Tested On`:
   ```markdown
   | Device | Board | OS | Status | Verified By |
   | MSI Model Name | `MS-XXXX` | Distro & Kernel | Working | @YourUsername |
   ```
2. In `models/database.json`, locate your board entry and set `"verified": true`:
   ```json
   "MS-XXXX": {
     "group": "G1_X",
     "name": "Your Model Name",
     "verified": true
   }
   ```
3. Submit a Pull Request titled `docs: add MS-XXXX to tested devices table`.

---

## 2. Reporting an Unmapped Model

If your laptop motherboard is not yet in our database:

1. Launch FrostCenter from the terminal:
   ```bash
   sudo python3 OFC.py
   ```
2. FrostCenter will detect that your board is not mapped and automatically display the interactive **Model Not Found** diagnostic window.
3. Click **Open Request on GitHub** to submit your read-only ACPI EC diagnostic probe, or click **Copy Diagnostic** to share it in an existing issue.
4. Maintainers will map your board's EC registers based on kernel driver sources (`msi-ec`) and the diagnostic dump.

---

## 3. Development Guidelines

* **Pure Linux Focus:** FrostCenter is designed for Linux distributions (Bazzite, Fedora, Ubuntu, Arch, Debian, etc.).
* **Zero Guessing on EC Registers:** Never guess raw EC register addresses. All address mappings must be cross-referenced with `msi-ec` kernel driver code, `isw`, or verified diagnostic dumps.
* **Testing & Simulation:** You can test the application on any PC, virtual machine, or WSL environment without needing an MSI laptop or root privileges:
  ```bash
  python3 tests/simulate_frostcenter.py                   # Simulated Raider GE75 (MS-17E9)
  python3 tests/simulate_frostcenter.py --board MS-16R4   # Simulated unverified model (GF63 Thin)
  python3 tests/simulate_frostcenter.py --board MS-16W2   # Simulated verified model (GF65 Thin)
  python3 tests/simulate_frostcenter.py --unmapped        # Test Model Not Found diagnostic window
  python3 tests/simulate_frostcenter.py --read-only       # Test read-only monitoring mode
  ```
