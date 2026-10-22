# Contributing to FrostCenter

Thank you for helping improve FrostCenter for the MSI Linux community! Whether you are testing a laptop, reporting an unmapped model, or submitting code improvements, your contributions are welcome.

---

## 1. Verifying a Working Laptop

If FrostCenter works on your MSI laptop model:

### Option A: Via the App (1-Click)
1. Open FrostCenter on your laptop and go to **Settings**.
2. Under **Device Verification & Community**, click **✓ Confirm on GitHub**.
3. A pre-filled issue report will open in your browser with your detected hardware and confirmed features. Click **Submit new issue**.

### Option B: Propose a PR Directly
You can add your laptop directly to the **Tested On** table in [`README.md`](README.md):
1. In `README.md`, add your device to the table under `## Tested On`:
   ```markdown
   | MSI Model Name | `MS-XXXX` | Distro & Kernel | Working | @YourUsername |
   ```
2. In `models/database.json`, find your board key and add `"verified": true`:
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
2. FrostCenter will detect that your model is missing and display the **Model Not Found** diagnostic window.
3. Click **Report on GitHub** to submit your read-only EC diagnostic probe, or copy the diagnostic output and open an issue.
4. We map the registers based on kernel sources (`msi-ec`) and community diagnostic dumps.

---

## 3. Development Guidelines

* **Pure Linux Focus:** FrostCenter is designed for Linux distributions (Bazzite, Fedora, Ubuntu, Arch, etc.).
* **Zero Guessing on EC Registers:** Never guess raw EC register addresses. All address mappings must be cross-referenced with `msi-ec` kernel driver code, `isw`, or verified diagnostic dumps.
* **Testing:** You can run the standalone UI and hardware simulator on any PC or virtual machine via:
  ```bash
  python3 tests/simulate_frostcenter.py
  ```
