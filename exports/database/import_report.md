# Repository import report

The importer uses a small allowlist, is idempotent, and records repository-relative paths and SHA-256 hashes.

- `docs/highlander_constitution.md` — canonical; `f7c6fc8efce1e0e96dfad28e993356f3f902e25494b11af0764a7126e75529fb`
- `exports/air_mail_special_external_claims.csv` — external; `3b2b3622080c74243c05c55531b17924ca73a4dd4c176b41bf38b6c6582fbbc5`
- `exports/take_five_play_this_inventory.csv` — highlander; `7b7181c5635b2c3cc4b678cf9e0c31730e26e471ae837f7f385c15a7bbda30cb`
- `exports/take_five_teachable_moments.csv` — highlander; `6c8730c9db2825009bd1cebc0aea1e65059e6daffbc9c1a9789f5f44f0bbfb5e`
- `fixtures/minor_pent_guardrail_doctrine.yaml` — canonical; `c0cb5b785d736220e362a0b264c8e8191abd3a85460a2d312a457e79202bd47a`

Skipped by design: PDFs, images, audio/video, scratch output, raw archives, and unstructured bulk notes.
