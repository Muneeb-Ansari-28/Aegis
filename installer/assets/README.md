# Aegis Installer Assets

This directory contains static assets required for packaging and distributing the Aegis desktop application.

---

## Asset Guidelines

- **Application Icons (`.ico`, `.png`)**:
  - `icon.ico`: Multi-resolution Windows icon (16x16, 32x32, 48x48, 64x64, 128x128, 256x256).
  - `icon.png`: High-resolution application icon (512x512) for Electron packager and documentation.
- **Installer Graphics**:
  - Setup background banner graphic (`164x314` or `493x314` for NSIS/Inno Setup installers).
  - Setup header logo (`150x57`).
- **Legal & License Documents**:
  - `license.txt` / `eula.rtf`: Plain-text or RTF End User License Agreement displayed during installation.
