"""
Team Analytics Chatbot MVP - Flask Web Server
"""

from flask import Flask, render_template, request, jsonify
import os
import json
from collections import defaultdict
from enhanced_bot import EnhancedTeamAnalyticsBot
from warehouse import LocalMetricsWarehouse

app = Flask(__name__)

# Initialize enhanced bot with default mode.
DATA_PATH = os.path.join(os.path.dirname(__file__), 'team_shape_summary.json')
MATCH_METADATA_PATH = os.path.join(os.path.dirname(__file__), 'match_metadata.json')
TEAM_MAPPING_PATH = os.path.join(os.path.dirname(__file__), 'team_mapping.json')
WAREHOUSE_DB_PATH = os.path.join(os.path.dirname(__file__), 'football_analytics.duckdb')
USE_LLM = False  # Default mode for requests that don't explicitly set "mode"
bot = EnhancedTeamAnalyticsBot(
    DATA_PATH,
    use_llm=USE_LLM,
    match_metadata_path=MATCH_METADATA_PATH,
    team_mapping_path=TEAM_MAPPING_PATH,
)
warehouse = LocalMetricsWarehouse(
    db_path=WAREHOUSE_DB_PATH,
    shape_summary_path=DATA_PATH,
    match_metadata_path=MATCH_METADATA_PATH,
    team_mapping_path=TEAM_MAPPING_PATH,
)


def _load_explorer_catalog():
    """Build a lightweight Team -> Match catalog for the UI explorer."""
    team_names = {"team_A": "Team A", "team_W": "Team W"}
    match_id = "match-1"
    match_date = "Unknown date"
    competition = "Competition"
    home_team = team_names["team_A"]
    away_team = team_names["team_W"]

    try:
        if os.path.exists(MATCH_METADATA_PATH):
            with open(MATCH_METADATA_PATH, "r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            match = metadata.get("match", {})
            teams = match.get("teams", {})
            match_id = str(match.get("match_id", "match-1"))
            match_date = str(match.get("date", "Unknown date"))
            competition = str(match.get("competition", "Competition"))
            home_team = str(teams.get("home", {}).get("name", home_team))
            away_team = str(teams.get("away", {}).get("name", away_team))

        if os.path.exists(TEAM_MAPPING_PATH) and os.path.exists(MATCH_METADATA_PATH):
            with open(TEAM_MAPPING_PATH, "r", encoding="utf-8") as handle:
                mapping = json.load(handle)
            with open(MATCH_METADATA_PATH, "r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            class_to_role = mapping.get("class_to_role", {})
            teams = metadata.get("match", {}).get("teams", {})
            for side in ("home", "away"):
                team_obj = teams.get(side, {})
                kit = str(team_obj.get("kit_color", "")).strip().lower()
                role = class_to_role.get(kit)
                if role in team_names and team_obj.get("name"):
                    team_names[role] = str(team_obj["name"])
    except Exception:
        # Keep graceful defaults for UI continuity.
        pass

    stage_counts = bot.data.get("stage_counts", {}) if bot.data else {}
    summary = bot.data.get("summary", {}) if bot.data else {}

    teams_payload = []
    for team_key in sorted(stage_counts.keys()):
        team_summary = summary.get(team_key, {}).get("attack", {}).get("build_up", {})
        shape = team_summary.get("shape", {})
        teams_payload.append(
            {
                "team_key": team_key,
                "name": team_names.get(team_key, team_key),
                "phases": int(sum((stage_counts.get(team_key, {}) or {}).values())),
                "shape_width": shape.get("width_avg"),
                "shape_depth": shape.get("depth_avg"),
            }
        )

    match_payload = {
        "match_id": match_id,
        "date": match_date,
        "competition": competition,
        "home_team": home_team,
        "away_team": away_team,
        "score": "N/A",
        "teams": [team_names.get("team_A", "Team A"), team_names.get("team_W", "Team W")],
    }

    return {"teams": teams_payload, "matches": [match_payload]}


EXPLORER_CATALOG = _load_explorer_catalog()


def _get_team_key_by_name(team_name: str):
    if not team_name:
        return None
    target = team_name.strip().lower()
    for team in EXPLORER_CATALOG.get("teams", []):
        if str(team.get("name", "")).strip().lower() == target:
            return team.get("team_key")
    return None


def _generate_report_bundle(query: str):
    """Return both report paths so UI can choose what to display."""
    rule_report = bot.answer_question(query, use_llm=False)
    warehouse_payload = None
    if warehouse.available:
        warehouse_payload = warehouse.generate_grounded_report(query)

    warehouse_report = (warehouse_payload or {}).get("report", "")
    warehouse_evidence = (warehouse_payload or {}).get("evidence", [])

    return {
        "rule_report": rule_report,
        "warehouse_report": warehouse_report,
        "warehouse_evidence": warehouse_evidence,
        "warehouse_available": warehouse.available,
        "warehouse_error": warehouse.error,
    }


def _generate_report_payload(query: str):
    """Backward-compatible single report path for chat endpoint behavior."""
    bundle = _generate_report_bundle(query)
    if bundle["warehouse_available"] and bundle["warehouse_report"]:
        return {
            "report": bundle["warehouse_report"],
            "evidence": bundle["warehouse_evidence"],
        }

    return {
        "report": (
            "Grounded warehouse is unavailable (duckdb not installed on this environment). "
            "Showing rule-based tactical answer instead.\n\n"
            f"{bundle['rule_report']}"
        ),
        "evidence": [],
    }


def _is_report_query(message: str) -> bool:
    text = (message or "").lower()
    report_terms = (
        "report",
        "tactical",
        "analysis",
        "insight",
        "summary",
    )
    return any(term in text for term in report_terms)

@app.route('/')
def index():
    """Serve the main chat interface."""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat API requests."""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        mode = str(data.get('mode', 'rule')).strip().lower()
        
        if not message:
            return jsonify({'response': 'Please enter a message.'})

        if _is_report_query(message):
            report_payload = _generate_report_payload(message)
            response = report_payload["report"]
        else:
            use_llm = mode == 'llm'
            response = bot.answer_question(message, use_llm=use_llm)

        # If user requested LLM but it's unavailable, provide a clear note.
        if mode == 'llm' and not bot.llm_available:
            response = f"{response}\n\n[Note] LLM mode is not available on this server. Showing rule-based response."
        
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'response': f'Sorry, an error occurred: {str(e)}'}), 500


@app.route('/api/report', methods=['POST'])
def report():
    """Generate tactical report(s) from rule and/or warehouse paths."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        source = str(data.get('source', 'auto')).strip().lower()
        if not query:
            return jsonify({'error': 'query is required'}), 400

        bundle = _generate_report_bundle(query)

        if source == 'rule':
            report_payload = {
                'report': bundle['rule_report'],
                'source_used': 'rule',
                **bundle,
            }
        elif source == 'warehouse':
            if bundle['warehouse_available'] and bundle['warehouse_report']:
                report_payload = {
                    'report': bundle['warehouse_report'],
                    'source_used': 'warehouse',
                    **bundle,
                }
            else:
                report_payload = {
                    'report': (
                        "Grounded warehouse is unavailable for this environment. "
                        "Install duckdb and restart to enable warehouse reports."
                    ),
                    'source_used': 'warehouse_unavailable',
                    **bundle,
                }
        elif source == 'both':
            report_payload = {
                'report': bundle['warehouse_report'] or bundle['rule_report'],
                'source_used': 'both',
                **bundle,
            }
        else:
            report_payload = {
                **_generate_report_payload(query),
                'source_used': 'auto',
                **bundle,
            }

        return jsonify(report_payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/passing-network')
def passing_network():
    """Return passing relation data for selected team."""
    team_name = request.args.get('team', '').strip()
    team_key = _get_team_key_by_name(team_name)
    if not team_key:
        return jsonify({'error': 'team is required'}), 400

    rel_payload = bot.rule_bot.pass_relations.get(team_key, {})
    relations = rel_payload.get("relations", []) if isinstance(rel_payload, dict) else []
    top_edges = sorted(
        relations,
        key=lambda item: item.get("total", 0),
        reverse=True
    )[:12]

    return jsonify({
        'team': team_name,
        'team_key': team_key,
        'total_relations': len(relations),
        'top_edges': top_edges,
    })


@app.route('/api/shot-map')
def shot_map():
    """
    Return attacking-lane activity proxy.
    Uses dribble destination lanes and final-attack phase counts as available data.
    """
    team_name = request.args.get('team', '').strip()
    team_key = _get_team_key_by_name(team_name)
    if not team_key:
        return jsonify({'error': 'team is required'}), 400

    dribble_payload = bot.rule_bot.dribble_relations.get(team_key, {})
    relations = dribble_payload.get("relations", []) if isinstance(dribble_payload, dict) else []

    lane_totals = defaultdict(int)
    for item in relations:
        lane = str(item.get("to_lane", "unknown"))
        lane_totals[lane] += int(item.get("total", 0))

    stage_counts = bot.data.get("stage_counts", {}).get(team_key, {}) if bot.data else {}
    final_attack_phases = int(stage_counts.get("final_attack", 0))

    return jsonify({
        'team': team_name,
        'team_key': team_key,
        'note': 'Shot-event feed is not loaded in this MVP. Showing attacking-lane proxy from dribble relations.',
        'final_attack_phases': final_attack_phases,
        'lane_activity': sorted(
            [{'lane': lane, 'count': count} for lane, count in lane_totals.items()],
            key=lambda x: x['count'],
            reverse=True
        ),
    })


@app.route('/api/dashboard')
def dashboard():
    """Return compact team dashboard metrics from currently loaded summary data."""
    match = EXPLORER_CATALOG.get("matches", [{}])[0]
    summary = bot.data.get("summary", {}) if bot.data else {}
    stage_counts = bot.data.get("stage_counts", {}) if bot.data else {}
    teams = []

    for team in EXPLORER_CATALOG.get("teams", []):
        team_key = team.get("team_key")
        attack_build = summary.get(team_key, {}).get("attack", {}).get("build_up", {})
        shape = attack_build.get("shape", {}) if isinstance(attack_build, dict) else {}
        teams.append({
            'team': team.get("name"),
            'team_key': team_key,
            'phases_total': int(sum((stage_counts.get(team_key, {}) or {}).values())),
            'build_up': int((stage_counts.get(team_key, {}) or {}).get("build_up", 0)),
            'progression': int((stage_counts.get(team_key, {}) or {}).get("progression", 0)),
            'final_attack': int((stage_counts.get(team_key, {}) or {}).get("final_attack", 0)),
            'formation_build_up': attack_build.get("formation", "n/a"),
            'width_avg': shape.get("width_avg"),
            'depth_avg': shape.get("depth_avg"),
            'stretch_index_avg': shape.get("stretch_index_avg"),
        })

    return jsonify({
        'match': match,
        'teams': teams,
    })


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'data_loaded': bot.data is not None,
        'llm_available': bot.llm_available,
        'warehouse_available': warehouse.available,
        'warehouse_error': warehouse.error,
        'warehouse_db_path': WAREHOUSE_DB_PATH,
        'default_mode': 'llm' if bot.use_llm else 'rule',
    })


@app.route('/api/explorer')
def explorer():
    """Return UI catalog data for Team -> Match -> Report browsing."""
    return jsonify(EXPLORER_CATALOG)

if __name__ == '__main__':
    print("=" * 60)
    print("Team Analytics Chatbot MVP - Starting Server")
    print("=" * 60)
    print("\nOpen your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
