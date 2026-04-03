# Delayed AEX option snapshot input

If you have delayed public strike prices for the next weekly expiry, save them to:

`input_aex/aex_option_chain_delayed_snapshot.json`

You can start from:

`input_aex/aex_option_chain_delayed_snapshot.example.json`

Supported simple flat schema:

- `spot_price`
- `options[]`
  - `expiry` or `expiry_unix`
  - `option_type` (`call` or `put`)
  - `strike`
  - `bid` / `ask` / `last`
  - optional `iv`

The workflow will normalize this file into the internal provider schema and use it in:

- `build_aex_option_surface_snapshot.py`
- `build_aex_structure_candidates.py`
- `generate_weekly_aex_option_review.py`

This is intended for delayed public chain snapshots when institutional provider files are not available.
