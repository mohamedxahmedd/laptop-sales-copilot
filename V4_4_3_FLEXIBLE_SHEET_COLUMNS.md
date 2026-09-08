# V4.4.3 — Flexible Google Sheet Columns

Fixes `Missing columns: specs`.

The live Google Sheet no longer needs a single `specs` column.
The importer now supports either:

1. A combined `specs / specifications / المواصفات` column, or
2. Separate columns for CPU, RAM, SSD/storage, GPU/VGA, VRAM, Touch, etc.

If `specs` is missing, the app automatically builds it from the hardware columns.
Direct structured columns override parsed values for better accuracy.

Only the laptop model column is mandatory.
