# Security Policy

## Supported Versions

Only the latest release and the current `main` branch receive security patches and updates.

| Version | Supported |
|---------|-----------|
| 0.1.x (latest) | :white_check_mark: |

---

## Hardware Safety & Scope

FrostCenter interacts directly with your laptop's **Embedded Controller (EC)** registers via `/dev/port` using root privileges. Because incorrect EC register writes can cause hardware instability or thermal issues, FrostCenter is engineered with safety boundaries:

- **Clamped Fan Speeds:** Speed offsets and manual curves are strictly clamped to safe bounds (0–150%).
- **Battery Thresholds:** Battery charge limits are strictly validated between 50% and 100%.
- **Read-Only Mode:** Available as a CLI flag (`--read-only`) and UI switch to safely monitor temperatures and fan speeds without writing any bytes to the EC.
- **Kernel Lockdown:** FrostCenter honors Linux kernel lockdown (`/sys/kernel/security/lockdown`) and will refuse to run if `/dev/port` access is blocked or restricted.

---

## Reporting a Vulnerability

If you discover a security vulnerability—especially anything related to privilege escalation, arbitrary EC register writes, or unsafe memory handling:

1. **Do NOT open a public GitHub issue.** Public issues disclose vulnerabilities before a patch can be developed and released.
2. **Submit via GitHub Private Vulnerability Reporting:**
   - Go to the **Security** tab of [FrostCenter on GitHub](https://github.com/gsriram24/FrostCenter/security).
   - Click **Report a vulnerability**.
3. **Or Email Maintainers Directly:**
   - Send details to [gsriram2403@gmail.com](mailto:gsriram2403@gmail.com) with the subject `[SECURITY] FrostCenter Vulnerability Report`.
   - Please include:
     - Description of the vulnerability.
     - Affected files and components.
     - Steps to reproduce or proof-of-concept (PoC).
     - Potential impact (e.g., unintended EC write, privilege bypass).

---

## Response Process

- **Acknowledgment:** We will acknowledge receipt of your report within **48 hours**.
- **Assessment:** Maintainers will verify the issue and determine severity.
- **Fix & Disclosure:** We will develop a fix in a private branch, coordinate disclosure timing with the reporter, and publish a security advisory alongside the patch release.
