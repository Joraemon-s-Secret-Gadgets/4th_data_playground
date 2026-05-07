"""Facade for Persona-L Le Labo crawler exports."""

from pipelines.persona_sources import format_persona_rows


BRAND = "Le Labo"
DEFAULT_OUTPUT_PATH = "data/lelabo_korea_fragrance_data.json"

__all__ = ["BRAND", "DEFAULT_OUTPUT_PATH", "format_persona_rows"]

# End of file.
