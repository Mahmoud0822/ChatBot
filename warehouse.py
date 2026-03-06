"""
Local metrics warehouse and grounded report generation for the MVP.
"""

import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional


class LocalMetricsWarehouse:
    """Persist transformed match metrics in DuckDB and generate grounded reports."""

    def __init__(
        self,
        db_path: str,
        shape_summary_path: str,
        match_metadata_path: Optional[str] = None,
        team_mapping_path: Optional[str] = None,
    ):
        self.db_path = db_path
        self.shape_summary_path = shape_summary_path
        self.match_metadata_path = match_metadata_path
        self.team_mapping_path = team_mapping_path
        self.available = False
        self.error: Optional[str] = None
        self.match_id = -1
        self._team_names = {"team_A": "Team A", "team_W": "Team W"}
        self._conn = None

        try:
            import duckdb  # pylint: disable=import-outside-toplevel

            self._conn = duckdb.connect(self.db_path)
            self.available = True
            self._bootstrap()
        except Exception as exc:  # pragma: no cover - defensive startup fallback
            self.error = str(exc)
            self.available = False

    def _bootstrap(self) -> None:
        """Initialize schema and load a first transformed dataset."""
        self._load_match_and_team_context()
        self._create_schema()
        self._ingest_shape_summary()

    def _load_match_and_team_context(self) -> None:
        """Load match id and human-readable team names from metadata when available."""
        metadata = self._safe_load_json(self.match_metadata_path)
        mapping = self._safe_load_json(self.team_mapping_path)

        if metadata:
            self.match_id = int(metadata.get("match", {}).get("match_id", -1))

        if not metadata or not mapping:
            return

        teams = metadata.get("match", {}).get("teams", {})
        class_to_role = mapping.get("class_to_role", {})

        for side in ("home", "away"):
            team_obj = teams.get(side, {})
            kit_color = str(team_obj.get("kit_color", "")).strip().lower()
            role = class_to_role.get(kit_color)
            if role in self._team_names and team_obj.get("name"):
                self._team_names[role] = str(team_obj["name"])

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS match_metrics (
                match_id INTEGER,
                team_key VARCHAR,
                team_name VARCHAR,
                mode VARCHAR,
                phase VARCHAR,
                frames_count INTEGER,
                formation VARCHAR,
                width_avg DOUBLE,
                depth_avg DOUBLE,
                h_spread_avg DOUBLE,
                v_spread_avg DOUBLE,
                stretch_index_avg DOUBLE,
                def_line_x_avg DOUBLE,
                mid_line_x_avg DOUBLE,
                att_line_x_avg DOUBLE,
                def_line_width_avg DOUBLE,
                mid_line_width_avg DOUBLE,
                att_line_width_avg DOUBLE,
                source_json VARCHAR,
                PRIMARY KEY (match_id, team_key, mode, phase)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_context_chunks (
                chunk_id VARCHAR PRIMARY KEY,
                match_id INTEGER,
                team_key VARCHAR,
                team_name VARCHAR,
                mode VARCHAR,
                phase VARCHAR,
                chunk_text VARCHAR,
                citation VARCHAR
            )
            """
        )

    def _ingest_shape_summary(self) -> None:
        """Transform the summary JSON into normalized rows and retrieval chunks."""
        payload = self._safe_load_json(self.shape_summary_path)
        if not payload:
            return

        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            return

        self._conn.execute("DELETE FROM match_metrics WHERE match_id = ?", [self.match_id])
        self._conn.execute(
            "DELETE FROM metric_context_chunks WHERE match_id = ?",
            [self.match_id],
        )

        rows: List[List[Any]] = []
        chunks: List[List[Any]] = []

        for team_key, by_mode in summary.items():
            if not isinstance(by_mode, dict):
                continue
            for mode, by_phase in by_mode.items():
                if not isinstance(by_phase, dict):
                    continue
                for phase, metrics in by_phase.items():
                    if not isinstance(metrics, dict):
                        continue

                    shape = metrics.get("shape", {}) or {}
                    lines = metrics.get("lines", {}) or {}
                    defensive = lines.get("defensive", {}) or {}
                    midfield = lines.get("midfield", {}) or {}
                    attacking = lines.get("attacking", {}) or {}

                    row = [
                        self.match_id,
                        team_key,
                        self._team_names.get(team_key, team_key),
                        str(mode),
                        str(phase),
                        int(metrics.get("frames_count", 0)),
                        str(metrics.get("formation", "unknown")),
                        self._num(shape.get("width_avg")),
                        self._num(shape.get("depth_avg")),
                        self._num(shape.get("h_spread_avg")),
                        self._num(shape.get("v_spread_avg")),
                        self._num(shape.get("stretch_index_avg")),
                        self._num(defensive.get("line_x_position_avg")),
                        self._num(midfield.get("line_x_position_avg")),
                        self._num(attacking.get("line_x_position_avg")),
                        self._num(defensive.get("width_avg")),
                        self._num(midfield.get("width_avg")),
                        self._num(attacking.get("width_avg")),
                        os.path.basename(self.shape_summary_path),
                    ]
                    rows.append(row)

                    chunk_text = self._build_chunk_text(
                        team_name=self._team_names.get(team_key, team_key),
                        mode=str(mode),
                        phase=str(phase),
                        row=row,
                    )
                    chunk_id = str(uuid.uuid4())[:8]
                    citation = f"match_metrics(match_id={self.match_id}, team={team_key}, mode={mode}, phase={phase})"
                    chunks.append(
                        [
                            chunk_id,
                            self.match_id,
                            team_key,
                            self._team_names.get(team_key, team_key),
                            str(mode),
                            str(phase),
                            chunk_text,
                            citation,
                        ]
                    )

        if rows:
            self._conn.executemany(
                """
                INSERT INTO match_metrics VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )
        if chunks:
            self._conn.executemany(
                """
                INSERT INTO metric_context_chunks VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                chunks,
            )

    def generate_grounded_report(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        """Retrieve relevant transformed chunks and synthesize a deterministic report."""
        if not self.available:
            return {
                "report": "Warehouse unavailable. Install duckdb and restart.",
                "evidence": [],
            }

        terms = self._query_terms(query)
        rows = self._conn.execute(
            """
            SELECT
                chunk_id,
                team_name,
                mode,
                phase,
                chunk_text,
                citation
            FROM metric_context_chunks
            WHERE match_id = ?
            """,
            [self.match_id],
        ).fetchall()

        scored: List[Dict[str, Any]] = []
        for row in rows:
            text = str(row[4]).lower()
            score = sum(1 for term in terms if term in text)
            if score > 0:
                scored.append(
                    {
                        "score": score,
                        "chunk_id": row[0],
                        "team_name": row[1],
                        "mode": row[2],
                        "phase": row[3],
                        "chunk_text": row[4],
                        "citation": row[5],
                    }
                )

        if not scored:
            scored = [
                {
                    "score": 0,
                    "chunk_id": row[0],
                    "team_name": row[1],
                    "mode": row[2],
                    "phase": row[3],
                    "chunk_text": row[4],
                    "citation": row[5],
                }
                for row in rows[:top_k]
            ]

        top = sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
        report_lines = ["Grounded Tactical Report", f"Query: {query}", ""]
        report_lines.append("Evidence-backed observations:")
        for item in top:
            report_lines.append(
                f"- {item['team_name']} | {item['mode']} | {item['phase']}: {item['chunk_text']}"
            )
        report_lines.append("")
        report_lines.append("Traceability:")
        for item in top:
            report_lines.append(f"- [{item['chunk_id']}] {item['citation']}")

        return {"report": "\n".join(report_lines), "evidence": top}

    def _build_chunk_text(self, team_name: str, mode: str, phase: str, row: List[Any]) -> str:
        return (
            f"{team_name} in {mode} {phase} used {row[6]}; "
            f"shape width {self._fmt(row[7])}m, depth {self._fmt(row[8])}m, "
            f"stretch index {self._fmt(row[11])}; "
            f"line heights D/M/A: {self._fmt(row[12])}/{self._fmt(row[13])}/{self._fmt(row[14])}m."
        )

    def _query_terms(self, query: str) -> List[str]:
        lowered = query.lower()
        base_terms = re.findall(r"[a-z0-9_]+", lowered)
        synonyms = {
            "report": ["analysis", "tactical"],
            "shape": ["width", "depth", "stretch"],
            "pressing": ["defense", "defensive"],
            "build": ["build_up"],
            "attack": ["final_attack", "attacking"],
        }
        expanded = set(base_terms)
        for term in list(base_terms):
            for syn in synonyms.get(term, []):
                expanded.add(syn)
        return list(expanded)

    @staticmethod
    def _safe_load_json(path: Optional[str]) -> Optional[Dict[str, Any]]:
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fmt(value: Any) -> str:
        if value is None:
            return "n/a"
        try:
            return f"{float(value):.1f}"
        except (TypeError, ValueError):
            return "n/a"
