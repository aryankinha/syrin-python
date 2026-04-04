"""ConfigSchemaExporter — export agent configuration as a clean, stable JSON schema dict."""

from __future__ import annotations

import json

from syrin.remote._schema import extract_agent_schema
from syrin.remote._types import AgentSchema, FieldSchema


def _flatten_fields(agent_schema: AgentSchema) -> list[dict[str, object]]:
    """Flatten all section fields from an AgentSchema into a sorted list of field dicts.

    Each dict contains ``name``, ``type``, ``description``, and ``default``.
    Fields are sorted by ``name`` (the dotted path) for deterministic ordering.

    Args:
        agent_schema: The full AgentSchema to flatten.

    Returns:
        List of field dicts sorted by name.
    """
    flat: list[dict[str, object]] = []

    def _collect(fields: list[FieldSchema]) -> None:
        for f in fields:
            flat.append(
                {
                    "name": f.path,
                    "type": f.type,
                    "description": f.description,
                    "default": f.default,
                }
            )
            if f.children:
                _collect(f.children)

    for section in agent_schema.sections.values():
        _collect(section.fields)

    flat.sort(key=lambda d: str(d["name"]))
    return flat


class ConfigSchemaExporter:
    """Exports agent configuration as a clean JSON schema dict for dashboards.

    Wraps :func:`extract_agent_schema` and flattens the result into a simple,
    stable structure that is easy to render in a UI or ship to an external
    config control plane.

    Example:
        >>> schema = ConfigSchemaExporter.export(agent)
        >>> schema["agent_id"]
        'my_agent:MyAgent'
        >>> json_str = ConfigSchemaExporter.export_json(agent)
    """

    @staticmethod
    def export(agent: object) -> dict[str, object]:
        """Export agent config schema as a stable dict with sorted fields.

        Uses :func:`extract_agent_schema` to extract field metadata from the
        agent's ``REMOTE_CONFIG_SECTIONS``. If the agent is not a
        ``RemoteConfigurable``, sections will be empty but the dict structure
        is always returned.

        Args:
            agent: A live agent instance (may or may not implement
                ``RemoteConfigurable`` on its config objects).

        Returns:
            Dict with keys ``agent_id``, ``sections``, and ``fields``.
            ``fields`` is a sorted list of dicts, each containing
            ``name``, ``type``, ``description``, and ``default``.
        """
        try:
            agent_schema = extract_agent_schema(agent)
        except Exception:
            agent_name = (
                getattr(agent, "_agent_name", None)
                or getattr(agent, "name", None)
                or type(agent).__name__
            )
            class_name = type(agent).__name__
            agent_id = f"{agent_name}:{class_name}"
            return {
                "agent_id": agent_id,
                "sections": [],
                "fields": [],
            }

        fields = _flatten_fields(agent_schema)
        section_keys = sorted(agent_schema.sections.keys())

        return {
            "agent_id": agent_schema.agent_id,
            "sections": section_keys,
            "fields": fields,
        }

    @staticmethod
    def export_json(agent: object) -> str:
        """Export agent config schema as a JSON string.

        Args:
            agent: A live agent instance.

        Returns:
            JSON string representation of :meth:`export`.
        """
        return json.dumps(ConfigSchemaExporter.export(agent), sort_keys=True, default=str)
