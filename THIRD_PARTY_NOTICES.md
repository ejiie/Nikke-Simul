# Third-party and source provenance

## Moris-kr/nikke-calc

- Repository: https://github.com/Moris-kr/nikke-calc
- Pinned commit: `b4f440594d9d88840305e5a5897584549a0264dc`
- License: MIT, Copyright (c) 2026 Jgaram.
- The original license is preserved verbatim in [third-party/nikke-calc.LICENSE](third-party/nikke-calc.LICENSE).
- P00 runs its unchanged web UI and Python reference from the ignored `.reference/nikke-calc` checkout. It does not yet vendor that application into `apps/web` or replace its engine.
- npm dependencies retain their respective licenses; their resolved versions are in the pinned upstream `site/package-lock.json`.

## Local Nikke-Dmg-Simulator

- Source supplied by the user: `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator`.
- Observed HEAD: `c10395cc6c46caaea2c58c13d400796549a7eb17`; the working tree contains uncommitted changes.
- No standalone root LICENSE was found. No MIT or other redistribution license is inferred for this source or for the entire new project.
- Two C# source files were copied without modifications: `OverloadProcessor.cs` and `OverloadOptionDto.cs`. Original namespaces and bytes are preserved. Source paths and SHA-256 hashes are in [sources.lock.json](sources.lock.json).
- An ignored local copy of 63 C#/project/XAML files supports baseline verification; [the source manifest](docs/legacy-source-manifest.json) records their hashes. Required game/account data remains ignored and is not part of the source distribution.

## Newly authored for Nikke-Simul

The solution/project scaffolding, PowerShell setup and verification wrappers, synthetic tests and smoke executable, source manifests, and project documentation were authored for this project. They are not features imported from nikke-calc. No repository-wide license is declared in P00.
