"""YAML/dict configuration describing which fields to score and how."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .matchers import Matcher, make_matcher


@dataclass
class LineItemSpec:
    """A repeated group of records (e.g. receipt menu lines) aligned with Hungarian matching."""

    path: str
    fields: dict[str, Matcher] = field(default_factory=dict)  # empty => infer from gold items
    match_on: dict[str, float] = field(default_factory=dict)  # field -> weight; empty => all
    min_similarity: float = 0.3


@dataclass
class Config:
    scalars: dict[str, Matcher] = field(default_factory=dict)
    line_items: dict[str, LineItemSpec] = field(default_factory=dict)
    default_matcher: Matcher = field(default_factory=Matcher)
    doc_pass_f1: float = 1.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Config:
        default = make_matcher(raw.get("default", "text"))
        scalars = {k: make_matcher(v) for k, v in (raw.get("scalars") or {}).items()}
        items: dict[str, LineItemSpec] = {}
        for path, spec in (raw.get("line_items") or {}).items():
            spec = spec or {}
            fields = {k: make_matcher(v) for k, v in (spec.get("fields") or {}).items()}
            match_on = spec.get("match_on") or {}
            if isinstance(match_on, list):
                match_on = {k: 1.0 for k in match_on}
            items[path] = LineItemSpec(
                path, fields, dict(match_on), float(spec.get("min_similarity", 0.3))
            )
        return cls(scalars, items, default, float(raw.get("doc_pass_f1", 1.0)))

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        return cls.from_dict(yaml.safe_load(Path(path).read_text()) or {})

    def to_dict(self) -> dict[str, Any]:
        def m(x: Matcher) -> dict[str, Any]:
            return {k: v for k, v in vars(x).items()}

        return {
            "default": m(self.default_matcher),
            "doc_pass_f1": self.doc_pass_f1,
            "scalars": {k: m(v) for k, v in self.scalars.items()},
            "line_items": {
                p: {
                    "match_on": s.match_on,
                    "min_similarity": s.min_similarity,
                    "fields": {k: m(v) for k, v in s.fields.items()},
                }
                for p, s in self.line_items.items()
            },
        }
