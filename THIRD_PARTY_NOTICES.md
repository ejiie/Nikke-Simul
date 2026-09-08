# Third-party and source provenance

## Moris-kr/nikke-calc

- Repository: https://github.com/Moris-kr/nikke-calc
- Pinned commit: `b4f440594d9d88840305e5a5897584549a0264dc`
- License: MIT, Copyright (c) 2026 Jgaram.
- The original license is preserved verbatim in [third-party/nikke-calc.LICENSE](third-party/nikke-calc.LICENSE).
- P00 runs its unchanged web UI and Python reference from the ignored `.reference/nikke-calc` checkout. It does not yet vendor that application into `apps/web` or replace its engine.
- npm dependencies retain their respective licenses; their resolved versions are in the pinned upstream `site/package-lock.json`.
- P01 adapts the request/header/option mapping structure from `scraper/profile_fetch.py`, `worker/src/index.js`, and `site/src/blablalink.ts`. It also copies lines 1–62 of `site/src/styles.css` into `apps/web/src/upstream-theme.css` with attribution. The original MIT notice applies to those upstream-derived portions. P01 UI dependencies have their own lock at `apps/web/package-lock.json`.

P02 uses pinned `data/base_stat_tables/collection.json`, `data/name_codes.json`, `data/parsed_nikke.json`, and the mapping/formula structure in `scraper/profile_fetch.py` and `calculator/damage.py` from the MIT-licensed upstream above. Data copies stay local and ignored. The MIT notice remains applicable to upstream-derived code; see [P02 provenance](docs/p02-source-map.ko.md).

## Local Nikke-Dmg-Simulator

- Source supplied by the user: `C:/Users/user/Documents/GitHub/Nikke-Dmg-Simulator`.
- Observed HEAD: `c10395cc6c46caaea2c58c13d400796549a7eb17`; the working tree contains uncommitted changes.
- No standalone root LICENSE was found. No MIT or other redistribution license is inferred for this source or for the entire new project.
- Two C# source files were copied without modifications: `OverloadProcessor.cs` and `OverloadOptionDto.cs`. Original namespaces and bytes are preserved. Source paths and SHA-256 hashes are in [sources.lock.json](sources.lock.json).
- An ignored local copy of 63 C#/project/XAML files supports baseline verification; [the source manifest](docs/legacy-source-manifest.json) records their hashes. Required game/account data remains ignored and is not part of the source distribution.
- P01 references the collection flow of `DataPipeline/crawler/getFromBlaLink.py` and the field relationships of `DataPipeline/etl/blabla_merger.py`; these are rewritten behind the new collector and C# normalization contracts. Source hashes and adaptation scope are documented separately.

P02 additionally copies `StatCalculator.cs`, `StatTable.cs`, `CubeStatDto.cs`, `RootDto.cs`, and `EffectType.cs` byte-for-byte from the local legacy source. It adapts the assembly order in `Entities/Nikke.cs` and damage brackets in `Combat/DamageCalculator.cs`; the charge formula follows the user's new decision. Exact paths and hashes are in [the P02 manifest](docs/p02-source-manifest.json).

The P02 buff correction follows the user's instruction and the shared native-stat buff contract in the legacy `Docs/DESIGN.md` §3.5, `Docs/FACTS.md`, and `Docs/VERIFICATION_LOG.md`. The legacy two-stage OL/skill wiring is not copied. Newly authored `StatBuffCalculator` merges permanent and active rate terms before calling the unchanged rounding implementation. Additional read-only source hashes and adaptation details are in [the correction record](docs/p02-buff-correction.ko.md).

## Newly authored for Nikke-Simul

The solution/project scaffolding, PowerShell setup and verification wrappers, synthetic tests and smoke executable, source manifests, and project documentation were authored for this project. They are not features imported from nikke-calc. No repository-wide license is declared in P00.
