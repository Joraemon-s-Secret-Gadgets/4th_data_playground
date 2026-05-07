"""Facade for Persona-L Byredo crawler exports."""

from pipelines.persona_sources import format_persona_rows


BRAND = "Byredo"
DEFAULT_OUTPUT_PATH = "data/byredo_korea_fragrance_data.json"

__all__ = ["BRAND", "DEFAULT_OUTPUT_PATH", "format_persona_rows"]

# End of file.
