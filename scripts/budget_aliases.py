"""Shared name-canonicalization for the budget migration scripts.

Both scripts/firefly_migration/migrate_budgets.py and
scripts/legacy_dompet_migration/migrate_budgets.py import this so a given
real-world place/trip resolves to the identical dompet.budgets row
regardless of which script runs first. Handles cross-wording merges that
app.db.budget.py's case-insensitive get-or-create alone can't catch (e.g.
"Allevia Mont Kiara" -> "Allevia"); incidental case-only variants (e.g.
"Summervilla Subang Jaya" / "SummerVilla Subang Jaya") are aliased to the
same canonical string here too, then get-or-create's LOWER(name) match
handles anything not explicitly listed.
"""

NAME_ALIASES = {
    "allevia mont kiara": "Allevia",
    "summervilla subang jaya": "Summervilla",
    "kuantan mar 2024": "Kuantan",
    "bentong dec 2024": "Bentong",
    "bentong sept 2024": "Bentong",
    "serendah jan 2025": "Serendah",
    "city hatchback - vmm 9538": "Honda City Hatchback - VMM9538",
}


def canonical_name(raw_name: str) -> str:
    return NAME_ALIASES.get(raw_name.lower(), raw_name)
