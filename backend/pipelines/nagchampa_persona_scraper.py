"""Facade for Persona-L Nag Champa crawler exports."""

from pipelines.persona_sources import format_persona_rows


BRAND = "Nag Champa"
DEFAULT_OUTPUT_PATH = "data/nagchampa_korea_fragrance_data.json"

__all__ = ["BRAND", "DEFAULT_OUTPUT_PATH", "format_persona_rows"]

# End of file.
