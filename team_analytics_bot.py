# Team Analytics Chatbot MVP - Enhanced Version
# Advanced natural language understanding for flexible question handling

import json
import os
import re
from typing import Dict, Any, List, Tuple, Optional
from difflib import get_close_matches
import math

class TeamAnalyticsBot:
    def __init__(self, data_path: str, match_metadata_path: Optional[str] = None, team_mapping_path: Optional[str] = None):
        """Initialize the bot with team data."""
        with open(data_path, 'r') as f:
            self.data = json.load(f)
        self.stage_counts = self.data['stage_counts']
        self.summary = self.data['summary']
        self.conversation_context = {}
        self.team_display_names = {'team_A': 'Team A', 'team_W': 'Team W'}
        self.team_alias_lookup = {}

        # Load optional mapping/metadata files to map Team A/W to real club names.
        self._load_team_identity(match_metadata_path, team_mapping_path)
        
        # Load pass and dribble relations data
        base_dir = os.path.dirname(data_path)
        self.pass_relations = {}
        self.dribble_relations = {}
        
        # Load team pass relations
        for team in ['team_A', 'team_W']:
            pass_file = os.path.join(base_dir, f'{team}_pass_relations.json')
            dribble_file = os.path.join(base_dir, f'{team}_dribble_relations.json')
            
            if os.path.exists(pass_file):
                with open(pass_file, 'r') as f:
                    self.pass_relations[team] = json.load(f)
            
            if os.path.exists(dribble_file):
                with open(dribble_file, 'r') as f:
                    self.dribble_relations[team] = json.load(f)
        
        # Define question patterns and their handlers
        self.question_patterns = {
            'status': [
                r'status', r'how many', r'count', r'phases', r'overview', r'summary', 
                r'information about', r'tell me about', r'what.*(?:have|did)', r'stats',
                r'statistics', r'performance', r'results'
            ],
            'formation': [
                r'formation', r'setup', r'shape.*formation', r'tactical setup',
                r'how.*setup', r'lineup', r'structure'
            ],
            'defensive_line': [
                r'back line', r'defensive line', r'defenders', r'back.*position',
                r'where.*defend', r'defensive position', r'backline'
            ],
            'midfield_line': [
                r'midfield line', r'mid line', r'midfielders', r'center.*position',
                r'middle.*position', r'where.*midfield'
            ],
            'attacking_line': [
                r'attacking line', r'attack line', r'front line', r'forwards',
                r'strikers', r'front.*position', r'where.*attack', r'attacking position'
            ],
            'all_lines': [
                r'all line', r'lines.*position', r'player positions', r'team shape',
                r'formation position', r'tactical position'
            ],
            'shape': [
                r'shape', r'width', r'depth', r'spread', r'coverage', r'field.*cover',
                r'stretch', r'compact', r'stretched'
            ],
            'comparison': [
                r'compare', r'vs', r'versus', r'difference', r'better', r'worse',
                r'which.*more', r'who.*better', r'contrast', r'who.*more', r'who.*less',
                r'which team', r'which one', r'who attacked', r'who had', r'more than'
            ],
            'coach_summary': [
                r'coach summary', r'coaching summary', r'coach mode', r'coaching mode',
                r'coaching report', r'training focus', r'game plan', r'match plan'
            ],
            'help': [
                r'help', r'what can', r'what.*do', r'how.*use', r'example',
                r'guide', r'assist', r'support'
            ],
            'passing': [
                r'pass', r'passes', r'passing', r'pass.*relation', r'pass.*pattern',
                r'pass.*network', r'pass.*flow', r'pass.*statistics', r'pass.*data',
                r'pass.*stats', r'pass.*info', r'pass.*analysis', r'pass.*summary',
                r'pass.*performance', r'pass.*metrics', r'pass.*numbers', r'pass.*figures'
            ],
            'dribbling': [
                r'dribble', r'dribbles', r'dribbling', r'dribble.*relation', r'dribble.*pattern',
                r'dribble.*network', r'dribble.*flow', r'dribble.*statistics', r'dribble.*data',
                r'dribble.*stats', r'dribble.*info', r'dribble.*analysis', r'dribble.*summary',
                r'dribble.*performance', r'dribble.*metrics', r'dribble.*numbers', r'dribble.*figures',
                r'dripl', r'dripple', r'dribel', r'driblle'
            ]
        }
        
        # Define phase patterns
        self.phase_patterns = {
            'build_up': [
                r'\bbuild[\s_-]?up\b', r'\bbuildup\b', r'\binitial\b', r'\bstart\b', r'\bbeginning\b',
                r'\bfirst phase\b', r'\bearly\b', r'\bdefensive.*phase\b'
            ],
            'progression': [
                r'\bprogression\b', r'\bprogress\b', r'\bmiddle\b', r'\btransition\b', r'\bmoving\b',
                r'\badvancing\b', r'\battacking.*transition\b'
            ],
            'final_attack': [
                r'\bfinal[\s_-]?attack\b', r'\bfinalattack\b', r'\bfinal\b', r'\bfinishing\b',
                r'\blast.*phase\b', r'\battacking.*phase\b', r'\battack.*phase\b'
            ]
        }
        
        # Define team patterns
        self.team_patterns = {
            'team_A': [r'team\s*a', r'teama', r'first team', r'team 1'],
            'team_W': [r'team\s*w', r'teamw', r'second team', r'team 2']
        }
        
        # Define mode patterns
        self.mode_patterns = {
            'attack': [r'attack', r'attacking', r'offense', r'offensive', r'with ball', r'in possession'],
            'defense': [r'defense', r'defending', r'defensive', r'without ball', r'out of possession']
        }
    
    def _load_team_identity(self, match_metadata_path: Optional[str], team_mapping_path: Optional[str]) -> None:
        """Load team aliases and display names from metadata/mapping files."""
        # Temporary defaults; may be overridden by metadata/color-based aliases below.
        self.team_alias_lookup.update({'a': 'team_A', 'w': 'team_W', 'team a': 'team_A', 'team w': 'team_W'})

        mapping_data = {}
        if team_mapping_path and os.path.exists(team_mapping_path):
            try:
                with open(team_mapping_path, 'r') as f:
                    mapping_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                mapping_data = {}

        metadata_data = {}
        if match_metadata_path and os.path.exists(match_metadata_path):
            try:
                with open(match_metadata_path, 'r') as f:
                    metadata_data = json.load(f)
            except (OSError, json.JSONDecodeError):
                metadata_data = {}

        # If mapping is present, respect its canonical names for A/W.
        letter_to_team = mapping_data.get('letter_to_team', {})
        for letter, mapped_name in letter_to_team.items():
            letter_lower = str(letter).strip().lower()
            if letter_lower in {'a', 'w'}:
                team_key = f"team_{letter.upper()}"
                self.team_display_names[team_key] = mapped_name
                self.team_alias_lookup[mapped_name.lower()] = team_key
                self.team_alias_lookup[f"team {letter_lower}"] = team_key
                self.team_alias_lookup[f"team_{letter_lower}"] = team_key

        # If metadata has real club names, map by color from team_mapping.
        teams_meta = metadata_data.get('match', {}).get('teams', {})
        class_to_role = mapping_data.get('class_to_role', {})
        for side in ('home', 'away'):
            team_info = teams_meta.get(side, {})
            kit_color = team_info.get('kit_color')
            role = class_to_role.get(kit_color)
            if role in {'team_A', 'team_W'}:
                real_name = team_info.get('name')
                short_name = team_info.get('short_name')
                if real_name:
                    self.team_display_names[role] = real_name
                    self.team_alias_lookup[real_name.lower()] = role
                if short_name:
                    self.team_alias_lookup[str(short_name).lower()] = role

        # User-facing convention: Team W refers to the white-kit team.
        # Team A refers to the non-white tracked outfield team (commonly red in this dataset).
        white_role = class_to_role.get('white')
        red_role = class_to_role.get('red')
        if white_role in {'team_A', 'team_W'}:
            self.team_alias_lookup['w'] = white_role
            self.team_alias_lookup['team w'] = white_role
            self.team_alias_lookup['team_w'] = white_role
            self.team_alias_lookup['white'] = white_role
            self.team_alias_lookup['white team'] = white_role
        if red_role in {'team_A', 'team_W'}:
            self.team_alias_lookup['a'] = red_role
            self.team_alias_lookup['team a'] = red_role
            self.team_alias_lookup['team_a'] = red_role

    def _display_team_name(self, team_key: str) -> str:
        """Return a user-facing team name."""
        return self.team_display_names.get(team_key, team_key.replace('_', ' ').title())

    def _resolve_team_key(self, team_name: str) -> Optional[str]:
        """Resolve a team identifier to canonical key (team_A/team_W)."""
        if not team_name:
            return None

        name = team_name.strip()
        name_lower = name.lower()

        # Exact key first
        if name in self.summary:
            return name
        if name_lower in self.summary:
            return name_lower

        compact = re.sub(r'[\s_]+', '', name_lower)
        for key in self.summary.keys():
            if key.lower() == name_lower or key.lower().replace('_', '') == compact:
                return key

        if name_lower in self.team_alias_lookup:
            alias_key = self.team_alias_lookup[name_lower]
            if alias_key in self.summary:
                return alias_key

        return None

    def _match_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns."""
        text_lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _extract_team(self, question: str) -> Optional[str]:
        """Extract team name from question using fuzzy matching."""
        question_lower = question.lower()

        # Try known aliases (real names/short names/letters) first.
        for alias, team_key in self.team_alias_lookup.items():
            if re.search(rf'\b{re.escape(alias)}\b', question_lower):
                if team_key in self.summary:
                    return team_key
        
        # Direct pattern matching
        for team_key, patterns in self.team_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    # Find actual key in data
                    resolved = self._resolve_team_key(team_key)
                    if resolved:
                        return resolved
        
        # Check for "team a", "team w", or "Team W" in various forms
        if re.search(r'\bteam\s*a\b', question_lower) or ' team a' in question_lower or 'team a ' in question_lower:
            for key in self.summary.keys():
                if 'a' in key.lower():
                    return key
        
        if re.search(r'\bteam\s*w\b', question_lower) or ' team w' in question_lower or 'team w ' in question_lower:
            for key in self.summary.keys():
                if 'w' in key.lower():
                    return key
        
        # Check if team was mentioned in previous context
        if 'last_team' in self.conversation_context:
            # If question is short, might be referring to previous team
            words = question_lower.split()
            if len(words) <= 3 and any(word in ['they', 'their', 'them', 'it'] for word in words):
                return self.conversation_context['last_team']
        
        return None
    
    def _extract_phase(self, question: str) -> Optional[str]:
        """Extract phase from question."""
        question_lower = question.lower()
        
        for phase_key, patterns in self.phase_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return phase_key
        
        return None
    
    def _extract_mode(self, question: str) -> Optional[str]:
        """Extract mode (attack/defense) from question, or None if unspecified."""
        question_lower = question.lower()
        
        # Check for explicit attack/defense context words
        attack_context = [r'\bwhile\s+attacking\b', r'\bwhile\s+attack\b', r'\bin\s+attack\b', r'\battacking\s+phase\b']
        defense_context = [r'\bwhile\s+defending\b', r'\bwhile\s+defense\b', r'\bin\s+defense\b', r'\bdefending\s+phase\b']
        
        # Check for explicit context first
        for pattern in attack_context:
            if re.search(pattern, question_lower):
                return 'attack'
        
        for pattern in defense_context:
            if re.search(pattern, question_lower):
                return 'defense'
        
        # General lexical cues
        if re.search(r'\battack(?:ing)?\b|\boffens(?:e|ive)\b|in possession|with ball', question_lower):
            return 'attack'
        
        if re.search(r'\bdefen(?:se|ce|sive|ding)\b|without ball|out of possession', question_lower):
            return 'defense'
        
        return None
    
    def _detect_intent(self, question: str) -> str:
        """Detect the intent of the question."""
        question_lower = question.lower()

        # Explicit coach mode request should override generic "summary" matches.
        if self._match_pattern(question_lower, self.question_patterns['coach_summary']):
            return 'coach_summary'

        # Prioritize high-signal intents that often include "how many".
        if self._match_pattern(question_lower, self.question_patterns['passing']):
            return 'passing'
        if self._match_pattern(question_lower, self.question_patterns['dribbling']):
            return 'dribbling'
        
        # Score each intent
        scores = {}
        for intent, patterns in self.question_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, question_lower))
                score += matches
            if score > 0:
                scores[intent] = score
        
        # Return the highest scoring intent
        if scores:
            return max(scores, key=scores.get)
        
        return 'unknown'

    def _stage_rank(self, stage: str) -> int:
        """Convert stage labels (D1/P2/F1) into comparable rank values."""
        if not stage:
            return 0
        stage = str(stage).strip().upper()
        match = re.match(r'^([DPF])(\d+)$', stage)
        if not match:
            return 0
        group, sub = match.group(1), int(match.group(2))
        base = {'D': 10, 'P': 20, 'F': 30}.get(group, 0)
        return base + sub

    def _sum_relation_totals(self, relation_data: Dict[str, Any]) -> Dict[str, int]:
        """Aggregate total/success/fail counts from relation records."""
        totals = {'total': 0, 'success': 0, 'fail': 0}
        for rel in relation_data.get('relations', []):
            totals['total'] += int(rel.get('total', 0))
            totals['success'] += int(rel.get('success', 0))
            totals['fail'] += int(rel.get('fail', 0))
        return totals

    def _progressive_relation_total(self, relation_data: Dict[str, Any]) -> int:
        """Count actions that move to a higher stage rank."""
        progressive_total = 0
        for rel in relation_data.get('relations', []):
            if self._stage_rank(rel.get('to_stage')) > self._stage_rank(rel.get('from_stage')):
                progressive_total += int(rel.get('total', 0))
        return progressive_total

    def _extract_passing_direction(self, question: str) -> Optional[str]:
        """Extract requested pass direction (forward/backward/lateral)."""
        question_lower = question.lower()
        if re.search(r'\bforward\b|\bprogressive\b|\bupfield\b', question_lower):
            return 'forward'
        if re.search(r'\bbackward\b|\bback\s+pass(?:es)?\b', question_lower):
            return 'backward'
        if re.search(r'\blateral\b|\bsideways\b|\bhorizontal\b', question_lower):
            return 'lateral'
        return None

    def _get_pass_direction_counts(self, team: str) -> Optional[Dict[str, Dict[str, int]]]:
        """Aggregate pass totals by direction using stage movement."""
        team_key = self._resolve_team_key(team) or team
        if team_key not in self.pass_relations:
            return None

        counts = {
            'forward': {'total': 0, 'success': 0, 'fail': 0},
            'backward': {'total': 0, 'success': 0, 'fail': 0},
            'lateral': {'total': 0, 'success': 0, 'fail': 0},
        }
        for rel in self.pass_relations[team_key].get('relations', []):
            from_rank = self._stage_rank(rel.get('from_stage'))
            to_rank = self._stage_rank(rel.get('to_stage'))
            if to_rank > from_rank:
                direction = 'forward'
            elif to_rank < from_rank:
                direction = 'backward'
            else:
                direction = 'lateral'
            counts[direction]['total'] += int(rel.get('total', 0))
            counts[direction]['success'] += int(rel.get('success', 0))
            counts[direction]['fail'] += int(rel.get('fail', 0))

        return counts
    
    def get_team_status(self, team_name: str) -> Dict[str, Any]:
        """Get the status/counts for a specific team."""
        team_key = self._resolve_team_key(team_name)
        if team_key and team_key in self.stage_counts:
            return {
                'team': team_key,
                'counts': self.stage_counts[team_key],
                'total': sum(self.stage_counts[team_key].values())
            }
        return None
    
    def get_formation(self, team: str, phase: str, mode: str = 'attack') -> Dict[str, Any]:
        """Get formation data for a team in a specific phase."""
        team_key = self._resolve_team_key(team)
        
        if not team_key or team_key not in self.summary:
            return None
        
        if mode not in self.summary[team_key]:
            return None
        
        if phase not in self.summary[team_key][mode]:
            return None
        
        phase_data = self.summary[team_key][mode][phase]
        return {
            'formation': phase_data.get('formation', 'N/A'),
            'formation_tuple': phase_data.get('formation_tuple_mode', []),
            'frames_count': phase_data.get('frames_count', 0),
            'avg_outfield_count': phase_data.get('avg_outfield_count', 0),
            'shape': phase_data.get('shape', {}),
            'lines': phase_data.get('lines', {})
        }
    
    def get_all_formations(self, team: str, mode: str = 'attack') -> Dict[str, Dict]:
        """Get all formations for a team."""
        formations = {}
        for phase in ['build_up', 'progression', 'final_attack']:
            formations[phase] = self.get_formation(team, phase, mode)
        return formations
    
    def get_line_positions(self, team: str, phase: str, mode: str = 'attack') -> Dict[str, Any]:
        """Get line positions for a team in a specific phase."""
        team_key = self._resolve_team_key(team)
        
        if not team_key or team_key not in self.summary:
            return None
        
        if mode not in self.summary[team_key]:
            return None
        
        if phase not in self.summary[team_key][mode]:
            return None
        
        phase_data = self.summary[team_key][mode][phase]
        lines = phase_data.get('lines', {})
        
        return {
            'defensive_line': lines.get('defensive', {}),
            'midfield_line': lines.get('midfield', {}),
            'attacking_line': lines.get('attacking', {}),
            'line_gaps': lines.get('line_gaps_x', {}),
            'goalkeeper': lines.get('gk', {})
        }
    
    def get_shape_metrics(self, team: str, phase: str, mode: str = 'attack') -> Dict[str, Any]:
        """Get shape metrics for a team in a specific phase."""
        team_key = self._resolve_team_key(team)
        
        if not team_key or team_key not in self.summary:
            return None
        
        if mode not in self.summary[team_key]:
            return None
        
        if phase not in self.summary[team_key][mode]:
            return None
        
        phase_data = self.summary[team_key][mode][phase]
        return phase_data.get('shape', {})
    
    def compare_teams(self, metric: str, phase: Optional[str] = None, mode: str = 'attack') -> str:
        """Compare teams on a specific metric."""
        teams = list(self.summary.keys())
        if len(teams) < 2:
            return "Need at least two teams to compare."
        
        team_a = teams[0]
        team_b = teams[1]
        
        if metric == 'status':
            status_a = self.get_team_status(team_a)
            status_b = self.get_team_status(team_b)
            return self._format_comparison_status(status_a, status_b)
        
        elif metric == 'formation':
            if phase:
                form_a = self.get_formation(team_a, phase, mode)
                form_b = self.get_formation(team_b, phase, mode)
                return self._format_comparison_formation(team_a, team_b, phase, form_a, form_b, mode)
            else:
                return self._format_comparison_all_formations(team_a, team_b, mode)
        
        return "Comparison not supported for this metric yet."
    
    def answer_question(self, question: str) -> str:
        """Answer a user question with advanced NLP."""
        question_lower = question.lower().strip()
        
        # Store question in context
        self.conversation_context['last_question'] = question
        
        # Extract entities
        team = self._extract_team(question)
        phase = self._extract_phase(question)
        explicit_mode = self._extract_mode(question)
        mode = explicit_mode or 'attack'
        intent = self._detect_intent(question)
        
        # Store team in context for follow-up questions
        if team:
            self.conversation_context['last_team'] = team
        
        # Handle help intent
        if intent == 'help':
            return self._get_help_message()
        
        # Handle comparison intent
        if intent == 'comparison':
            if phase:
                return self.compare_teams('formation', phase, mode)
            return self.compare_teams('status')
        
        # If no team found, try to use context or ask user
        if not team:
            # Check if this is a follow-up question
            if 'last_team' in self.conversation_context:
                team = self.conversation_context['last_team']
            else:
                return "Please specify which team you're asking about (Team A or Team W)."
        
        # Handle different intents
        if intent == 'coach_summary':
            return self._format_coach_summary(team)

        if intent == 'status':
            status = self.get_team_status(team)
            if status:
                return self._format_status(status)
            return f"No status data found for {team}."
        
        elif intent == 'formation':
            if phase:
                formation = self.get_formation(team, phase, mode)
                if formation:
                    return self._format_formation(team, phase, formation, mode)
                return f"No formation data found for {team} in {phase} phase ({mode} mode)."
            else:
                if explicit_mode is None:
                    attack_formations = self.get_all_formations(team, 'attack')
                    defense_formations = self.get_all_formations(team, 'defense')
                    return self._format_formations_all_modes(team, attack_formations, defense_formations)
                formations = self.get_all_formations(team, mode)
                return self._format_formations(team, formations, mode)
        
        elif intent == 'defensive_line':
            if phase:
                lines = self.get_line_positions(team, phase, mode)
                if lines and 'defensive_line' in lines:
                    return self._format_defensive_line(team, phase, lines['defensive_line'], mode)
                return f"No defensive line data found for {team} in {phase} phase ({mode} mode)."
            else:
                # Return all phases
                all_lines = {}
                for ph in ['build_up', 'progression', 'final_attack']:
                    lines = self.get_line_positions(team, ph, mode)
                    if lines and 'defensive_line' in lines:
                        all_lines[ph] = lines['defensive_line']
                return self._format_all_defensive_lines(team, all_lines, mode)
        
        elif intent == 'midfield_line':
            if phase:
                lines = self.get_line_positions(team, phase, mode)
                if lines and 'midfield_line' in lines:
                    return self._format_midfield_line(team, phase, lines['midfield_line'], mode)
                return f"No midfield line data found for {team} in {phase} phase ({mode} mode)."
            else:
                # Return all phases
                all_lines = {}
                for ph in ['build_up', 'progression', 'final_attack']:
                    lines = self.get_line_positions(team, ph, mode)
                    if lines and 'midfield_line' in lines:
                        all_lines[ph] = lines['midfield_line']
                return self._format_all_midfield_lines(team, all_lines, mode)
        
        elif intent == 'attacking_line':
            if phase:
                lines = self.get_line_positions(team, phase, mode)
                if lines and 'attacking_line' in lines:
                    return self._format_attacking_line(team, phase, lines['attacking_line'], mode)
                return f"No attacking line data found for {team} in {phase} phase ({mode} mode)."
            else:
                # Return all phases
                all_lines = {}
                for ph in ['build_up', 'progression', 'final_attack']:
                    lines = self.get_line_positions(team, ph, mode)
                    if lines and 'attacking_line' in lines:
                        all_lines[ph] = lines['attacking_line']
                return self._format_all_attacking_lines(team, all_lines, mode)
        
        elif intent == 'all_lines':
            if phase:
                lines = self.get_line_positions(team, phase, mode)
                if lines:
                    return self._format_lines(team, phase, lines, mode)
                return f"No line position data found for {team} in {phase} phase ({mode} mode)."
            else:
                # Return summary for all phases
                all_lines = {}
                for ph in ['build_up', 'progression', 'final_attack']:
                    all_lines[ph] = self.get_line_positions(team, ph, mode)
                return self._format_all_lines_summary(team, all_lines, mode)
        
        elif intent == 'shape':
            if phase:
                shape = self.get_shape_metrics(team, phase, mode)
                if shape:
                    return self._format_shape(team, phase, shape, mode)
                return f"No shape data found for {team} in {phase} phase ({mode} mode)."
            else:
                # Return shape for all phases
                all_shapes = {}
                for ph in ['build_up', 'progression', 'final_attack']:
                    all_shapes[ph] = self.get_shape_metrics(team, ph, mode)
                return self._format_all_shapes(team, all_shapes, mode)
        
        elif intent == 'passing':
            direction = self._extract_passing_direction(question)
            if direction:
                return self._format_pass_direction(team, direction)
            return self._format_passing_relations(team)
        
        elif intent == 'dribbling':
            return self._format_dribbling_relations(team)
        
        # Try to give a helpful response based on what we can extract
        if team and phase:
            # Try to get comprehensive data
            formation = self.get_formation(team, phase, mode)
            if formation:
                return self._format_comprehensive(team, phase, formation, mode)
        
        # If we have a Team Wut unclear intent, provide a summary
        if team:
            return self._format_team_summary(team)
        
        # Fallback to help
        return self._get_help_message()
    
    def _format_status(self, status: Dict) -> str:
        """Format team status for display."""
        team_name = self._display_team_name(status['team'])
        counts = status['counts']
        total = status['total']
        
        return f"""**{team_name} Status**

**Stage Counts:**
- Build Up: {counts['build_up']} phases
- Progression: {counts['progression']} phases  
- Final Attack: {counts['final_attack']} phases
- **Total: {total} phases**

This represents the number of times the team entered each attacking phase during the match."""
    
    def _format_formation(self, team: str, phase: str, formation: Dict, mode: str) -> str:
        """Format formation data."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        return f"""**{team_name} - {phase_name} Phase ({mode_name})**

**Formation:** {formation['formation']}
- Structure: {'-'.join(map(str, formation['formation_tuple']))}
- Frames Analyzed: {formation['frames_count']}
- Average Outfield Players: {formation['avg_outfield_count']:.1f}"""
    
    def _format_formations(self, team: str, formations: Dict, mode: str) -> str:
        """Format formations for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} Formations ({mode_name})**\n"]
        
        for phase, formation in formations.items():
            if formation:
                phase_name = phase.replace('_', ' ').title()
                lines.append(f"**{phase_name}:** {formation['formation']} (over {formation['frames_count']} frames)")
        
        return '\n'.join(lines)

    def _format_formations_all_modes(self, team: str, attack_formations: Dict, defense_formations: Dict) -> str:
        """Format formations across phases for both attack and defense."""
        team_name = self._display_team_name(team)
        lines = [f"**{team_name} Formations (All Phases)**\n", "**Attack:**"]

        for phase in ['build_up', 'progression', 'final_attack']:
            formation = attack_formations.get(phase)
            if formation:
                phase_name = phase.replace('_', ' ').title()
                lines.append(f"- {phase_name}: {formation['formation']} (over {formation['frames_count']} frames)")

        lines.append("\n**Defense:**")
        for phase in ['build_up', 'progression', 'final_attack']:
            formation = defense_formations.get(phase)
            if formation:
                phase_name = phase.replace('_', ' ').title()
                lines.append(f"- {phase_name}: {formation['formation']} (over {formation['frames_count']} frames)")

        return '\n'.join(lines)
    
    def _format_defensive_line(self, team: str, phase: str, line: Dict, mode: str) -> str:
        """Format defensive line data."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        return f"""**{team_name} Defensive Line - {phase_name} Phase ({mode_name})**

**Position:** X = {line.get('line_x_position_avg', 'N/A'):.1f}
**Width:** {line.get('width_avg', 'N/A'):.1f}m
**Lateral Spread:** {line.get('lateral_spread_avg', 'N/A'):.1f}m

The defensive line represents the average position of the back defenders on the pitch."""
    
    def _format_midfield_line(self, team: str, phase: str, line: Dict, mode: str) -> str:
        """Format midfield line data."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        return f"""**{team_name} Midfield Line - {phase_name} Phase ({mode_name})**

**Position:** X = {line.get('line_x_position_avg', 'N/A'):.1f}
**Width:** {line.get('width_avg', 'N/A'):.1f}m
**Lateral Spread:** {line.get('lateral_spread_avg', 'N/A'):.1f}m

The midfield line represents the average position of the central midfielders."""
    
    def _format_attacking_line(self, team: str, phase: str, line: Dict, mode: str) -> str:
        """Format attacking line data."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        return f"""**{team_name} Attacking Line - {phase_name} Phase ({mode_name})**

**Position:** X = {line.get('line_x_position_avg', 'N/A'):.1f}
**Width:** {line.get('width_avg', 'N/A'):.1f}m
**Lateral Spread:** {line.get('lateral_spread_avg', 'N/A'):.1f}m

The attacking line represents the average position of the forward players."""
    
    def _format_all_defensive_lines(self, team: str, all_lines: Dict, mode: str) -> str:
        """Format defensive line positions for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} Defensive Line Positions ({mode_name})**\n"]
        lines.append("Here are the back line positions across all phases:\n")
        
        for phase, line_data in all_lines.items():
            if line_data:
                phase_name = phase.replace('_', ' ').title()
                pos = line_data.get('line_x_position_avg', 'N/A')
                width = line_data.get('width_avg', 'N/A')
                spread = line_data.get('lateral_spread_avg', 'N/A')
                lines.append(f"**{phase_name}:** Position X = {pos:.1f}m, Width = {width:.1f}m, Spread = {spread:.1f}m")
        
        return '\n'.join(lines)
    
    def _format_all_midfield_lines(self, team: str, all_lines: Dict, mode: str) -> str:
        """Format midfield line positions for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} Midfield Line Positions ({mode_name})**\n"]
        lines.append("Here are the midfield line positions across all phases:\n")
        
        for phase, line_data in all_lines.items():
            if line_data:
                phase_name = phase.replace('_', ' ').title()
                pos = line_data.get('line_x_position_avg', 'N/A')
                width = line_data.get('width_avg', 'N/A')
                spread = line_data.get('lateral_spread_avg', 'N/A')
                lines.append(f"**{phase_name}:** Position X = {pos:.1f}m, Width = {width:.1f}m, Spread = {spread:.1f}m")
        
        return '\n'.join(lines)
    
    def _format_all_attacking_lines(self, team: str, all_lines: Dict, mode: str) -> str:
        """Format attacking line positions for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} Attacking Line Positions ({mode_name})**\n"]
        lines.append("Here are the attacking line positions across all phases:\n")
        
        for phase, line_data in all_lines.items():
            if line_data:
                phase_name = phase.replace('_', ' ').title()
                pos = line_data.get('line_x_position_avg', 'N/A')
                width = line_data.get('width_avg', 'N/A')
                spread = line_data.get('lateral_spread_avg', 'N/A')
                lines.append(f"**{phase_name}:** Position X = {pos:.1f}m, Width = {width:.1f}m, Spread = {spread:.1f}m")
        
        return '\n'.join(lines)
    
    def _format_lines(self, team: str, phase: str, lines: Dict, mode: str) -> str:
        """Format all line positions."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        def_line = lines.get('defensive_line', {})
        mid_line = lines.get('midfield_line', {})
        att_line = lines.get('attacking_line', {})
        gaps = lines.get('line_gaps', {})
        
        return f"""**{team_name} Line Positions - {phase_name} Phase ({mode_name})**

**Defensive Line:**
- Position: X = {def_line.get('line_x_position_avg', 'N/A'):.1f}
- Width: {def_line.get('width_avg', 'N/A'):.1f}m

**Midfield Line:**
- Position: X = {mid_line.get('line_x_position_avg', 'N/A'):.1f}
- Width: {mid_line.get('width_avg', 'N/A'):.1f}m

**Attacking Line:**
- Position: X = {att_line.get('line_x_position_avg', 'N/A'):.1f}
- Width: {att_line.get('width_avg', 'N/A'):.1f}m

**Line Gaps:**
- Def to Mid: {gaps.get('gap_def_mid_x_avg', 'N/A'):.1f}m
- Mid to Att: {gaps.get('gap_mid_att_x_avg', 'N/A'):.1f}m"""
    
    def _format_all_lines_summary(self, team: str, all_lines: Dict, mode: str) -> str:
        """Format all line positions summary for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} All Line Positions ({mode_name})**\n"]
        
        for phase, lines_data in all_lines.items():
            if lines_data:
                phase_name = phase.replace('_', ' ').title()
                def_pos = lines_data.get('defensive_line', {}).get('line_x_position_avg', 0)
                mid_pos = lines_data.get('midfield_line', {}).get('line_x_position_avg', 0)
                att_pos = lines_data.get('attacking_line', {}).get('line_x_position_avg', 0)
                lines.append(f"\n**{phase_name}:**")
                lines.append(f"  Defensive: X={def_pos:.1f}m")
                lines.append(f"  Midfield: X={mid_pos:.1f}m")
                lines.append(f"  Attacking: X={att_pos:.1f}m")
        
        return '\n'.join(lines)
    
    def _format_shape(self, team: str, phase: str, shape: Dict, mode: str) -> str:
        """Format shape metrics."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        return f"""**{team_name} Shape Metrics - {phase_name} Phase ({mode_name})**

**Width:**
- Average: {shape.get('width_avg', 'N/A'):.1f}m
- Min: {shape.get('width_min', 'N/A'):.1f}m
- Max: {shape.get('width_max', 'N/A'):.1f}m

**Depth:**
- Average: {shape.get('depth_avg', 'N/A'):.1f}m
- Min: {shape.get('depth_min', 'N/A'):.1f}m
- Max: {shape.get('depth_max', 'N/A'):.1f}m

**Spread:**
- Horizontal: {shape.get('h_spread_avg', 'N/A'):.1f}m
- Vertical: {shape.get('v_spread_avg', 'N/A'):.1f}m
- Stretch Index: {shape.get('stretch_index_avg', 'N/A'):.3f}"""
    
    def _format_all_shapes(self, team: str, all_shapes: Dict, mode: str) -> str:
        """Format shape metrics for all phases."""
        team_name = self._display_team_name(team)
        mode_name = mode.title()
        
        lines = [f"**{team_name} Shape Metrics Across All Phases ({mode_name})**\n"]
        
        for phase, shape in all_shapes.items():
            if shape:
                phase_name = phase.replace('_', ' ').title()
                width = shape.get('width_avg', 0)
                depth = shape.get('depth_avg', 0)
                stretch = shape.get('stretch_index_avg', 0)
                lines.append(f"**{phase_name}:** Width={width:.1f}m, Depth={depth:.1f}m, Stretch={stretch:.3f}")
        
        return '\n'.join(lines)
    
    def _format_comprehensive(self, team: str, phase: str, formation: Dict, mode: str) -> str:
        """Format comprehensive data for a team in a phase."""
        team_name = self._display_team_name(team)
        phase_name = phase.replace('_', ' ').title()
        mode_name = mode.title()
        
        lines_data = formation.get('lines', {})
        shape = formation.get('shape', {})
        
        return f"""**{team_name} - {phase_name} Phase ({mode_name}) - Complete Overview**

**Formation:** {formation['formation']} ({'-'.join(map(str, formation['formation_tuple']))})

**Line Positions:**
- Defensive: X = {lines_data.get('defensive', {}).get('line_x_position_avg', 0):.1f}m
- Midfield: X = {lines_data.get('midfield', {}).get('line_x_position_avg', 0):.1f}m  
- Attacking: X = {lines_data.get('attacking', {}).get('line_x_position_avg', 0):.1f}m

**Shape:**
- Width: {shape.get('width_avg', 0):.1f}m
- Depth: {shape.get('depth_avg', 0):.1f}m
- Stretch: {shape.get('stretch_index_avg', 0):.3f}"""
    
    def _format_team_summary(self, team: str) -> str:
        """Format a general summary for a team."""
        team_name = self._display_team_name(team)
        status = self.get_team_status(team)
        
        lines = [f"**{team_name} Summary**\n"]
        
        if status:
            lines.append(f"**Total Phases:** {status['total']}")
            lines.append(f"- Build Up: {status['counts']['build_up']}")
            lines.append(f"- Progression: {status['counts']['progression']}")
            lines.append(f"- Final Attack: {status['counts']['final_attack']}\n")
        
        lines.append("You can ask me about:")
        lines.append("- Formations in specific phases")
        lines.append("- Line positions (defensive, midfield, attacking)")
        lines.append("- Shape metrics and field coverage")
        lines.append("- Comparisons between teams")
        
        return '\n'.join(lines)

    def _format_coach_summary(self, team: str) -> str:
        """Format a coach-focused summary with actionable points."""
        team_key = self._resolve_team_key(team) or team
        team_name = self._display_team_name(team_key)
        status = self.get_team_status(team_key)
        if not status:
            return f"No team data found for {team_name}."

        counts = status['counts']
        total_phases = max(status['total'], 1)
        progression_rate = counts['progression'] / total_phases * 100.0
        final_attack_rate = counts['final_attack'] / total_phases * 100.0

        attack_forms = self.get_all_formations(team_key, 'attack')
        defense_forms = self.get_all_formations(team_key, 'defense')

        pass_data = self.pass_relations.get(team_key, {})
        pass_totals = self._sum_relation_totals(pass_data) if pass_data else {'total': 0, 'success': 0, 'fail': 0}
        progressive_passes = self._progressive_relation_total(pass_data) if pass_data else 0
        pass_success_rate = (pass_totals['success'] / pass_totals['total'] * 100.0) if pass_totals['total'] else 0.0
        progressive_pass_rate = (progressive_passes / pass_totals['total'] * 100.0) if pass_totals['total'] else 0.0

        dribble_data = self.dribble_relations.get(team_key, {})
        dribble_totals = self._sum_relation_totals(dribble_data) if dribble_data else {'total': 0, 'success': 0, 'fail': 0}
        progressive_dribbles = self._progressive_relation_total(dribble_data) if dribble_data else 0
        dribble_success_rate = (dribble_totals['success'] / dribble_totals['total'] * 100.0) if dribble_totals['total'] else 0.0

        attack_final_shape = self.get_shape_metrics(team_key, 'final_attack', 'attack') or {}
        attack_prog_lines = self.get_line_positions(team_key, 'progression', 'attack') or {}
        defense_prog_shape = self.get_shape_metrics(team_key, 'progression', 'defense') or {}

        final_width = float(attack_final_shape.get('width_avg', 0) or 0)
        final_depth = float(attack_final_shape.get('depth_avg', 0) or 0)
        def_prog_width = float(defense_prog_shape.get('width_avg', 0) or 0)
        gaps = attack_prog_lines.get('line_gaps', {}) if attack_prog_lines else {}
        gap_def_mid = float(gaps.get('gap_def_mid_x_avg', 0) or 0)
        gap_mid_att = float(gaps.get('gap_mid_att_x_avg', 0) or 0)

        coaching_points = []
        if final_attack_rate < 35:
            coaching_points.append("Increase progression-to-final-third conversion with third-man runs and earlier support around the ball.")
        else:
            coaching_points.append("Final-third access rate is solid; focus on chance quality and final pass timing.")

        if pass_totals['total'] and progressive_pass_rate < 45:
            coaching_points.append("Raise progressive pass volume by creating better interior receiving angles in possession.")

        if dribble_totals['total'] and dribble_success_rate < 55:
            coaching_points.append("Improve 1v1 efficiency in wide channels with isolation patterns and immediate support.")

        if final_width < 30:
            coaching_points.append("Final-attack shape is narrow; keep weak-side width to stretch the back line.")

        if gap_def_mid > 16 or gap_mid_att > 18:
            coaching_points.append("Vertical spacing is stretched in progression; reduce line gaps for cleaner support distances.")

        if def_prog_width > 32:
            coaching_points.append("Defensive progression block is wide; improve central compactness without losing pressing access.")

        if not coaching_points:
            coaching_points.append("Current structure is balanced; prioritize transition speed and repeated execution under pressure.")

        def form_name(forms: Dict[str, Dict], phase: str) -> str:
            form = forms.get(phase, {})
            return form.get('formation', 'N/A') if form else 'N/A'

        return f"""**{team_name} Coach Summary Mode**

**Phase Profile:**
- Build Up: {counts['build_up']}
- Progression: {counts['progression']} ({progression_rate:.1f}% of phases)
- Final Attack: {counts['final_attack']} ({final_attack_rate:.1f}% of phases)

**Formations (Reference):**
- Attack: Build Up {form_name(attack_forms, 'build_up')} | Progression {form_name(attack_forms, 'progression')} | Final Attack {form_name(attack_forms, 'final_attack')}
- Defense: Build Up {form_name(defense_forms, 'build_up')} | Progression {form_name(defense_forms, 'progression')} | Final Attack {form_name(defense_forms, 'final_attack')}

**Ball Progression Indicators:**
- Passes: {pass_totals['total']} total, {pass_success_rate:.1f}% success, {progressive_passes} progressive ({progressive_pass_rate:.1f}%)
- Dribbles: {dribble_totals['total']} total, {dribble_success_rate:.1f}% success, {progressive_dribbles} progressive

**Shape & Spacing Check:**
- Final attack width/depth: {final_width:.1f}m / {final_depth:.1f}m
- Progression line gaps: Def-Mid {gap_def_mid:.1f}m, Mid-Att {gap_mid_att:.1f}m
- Defensive width in progression: {def_prog_width:.1f}m

**Training Focus (Next Session):**
{chr(10).join(f"- {point}" for point in coaching_points)}"""
    
    def _format_comparison_status_legacy(self, status_a: Dict, status_b: Dict) -> str:
        """Legacy comparison formatter retained for reference; not used."""
        team_a_name = self._display_team_name(status_a['team'])
        team_b_name = self._display_team_name(status_b['team'])
        
        counts_a = status_a['counts']
        counts_b = status_b['counts']
        
        # Calculate effectiveness metrics
        final_attack_a = counts_a['final_attack']
        final_attack_b = counts_b['final_attack']
        total_a = status_a['total']
        total_b = status_b['total']
        
        # Calculate attack efficiency (Final Attack / Total phases)
        efficiency_a = (final_attack_a / total_a * 100) if total_a > 0 else 0
        efficiency_b = (final_attack_b / total_b * 100) if total_b > 0 else 0
        
        # Determine which team is more effective
        more_effective = team_a_name if final_attack_a > final_attack_b else team_b_name
        more_efficient = team_a_name if efficiency_a > efficiency_b else team_b_name
        
        # Build analysis insights
        insights = []
        
        if final_attack_a > final_attack_b:
            insights.append(f"🎯 **{team_a_name} was more effective** - reached final attack {final_attack_a - final_attack_b} more times")
        elif final_attack_b > final_attack_a:
            insights.append(f"🎯 **{team_b_name} was more effective** - reached final attack {final_attack_b - final_attack_a} more times")
        else:
            insights.append(f"⚖️ **Both teams equally effective** - reached final attack the same number of times")
        
        if efficiency_a > efficiency_b:
            insights.append(f"📈 **{team_a_name} more efficient** - {efficiency_a:.1f}% of phases reached final attack vs {efficiency_b:.1f}%")
        elif efficiency_b > efficiency_a:
            insights.append(f"📈 **{team_b_name} more efficient** - {efficiency_b:.1f}% of phases reached final attack vs {efficiency_a:.1f}%")
        
        # Analyze playing style
        if counts_a['build_up'] > counts_b['build_up']:
            insights.append(f"🏗️ **{team_a_name}** focused more on build-up play ({counts_a['build_up']} vs {counts_b['build_up']})")
        elif counts_b['build_up'] > counts_a['build_up']:
            insights.append(f"🏗️ **{team_b_name}** focused more on build-up play ({counts_b['build_up']} vs {counts_a['build_up']})")
        
        return f"""**Team Comparison - Performance Analysis**

| Phase | {team_a_name} | {team_b_name} |
|-------|---------------|---------------|
| Build Up | {counts_a['build_up']} | {counts_b['build_up']} |
| Progression | {counts_a['progression']} | {counts_b['progression']} |
| Final Attack | {counts_a['final_attack']} | {counts_b['final_attack']} |
| **Total** | **{total_a}** | **{total_b}** |
| **Attack Efficiency** | **{efficiency_a:.1f}%** | **{efficiency_b:.1f}%** |

**Key Insights:**
{chr(10).join(f"• {insight}" for insight in insights)}

**Summary:**
{more_effective} was more effective at reaching final attacking positions, while {more_efficient} was more efficient at converting build-up into attacks."""
    
    def _format_comparison_status(self, status_a: Dict, status_b: Dict) -> str:
        """Format status comparison between teams with effectiveness analysis."""
        team_a_name = self._display_team_name(status_a['team'])
        team_b_name = self._display_team_name(status_b['team'])

        counts_a = status_a['counts']
        counts_b = status_b['counts']

        final_attack_a = counts_a['final_attack']
        final_attack_b = counts_b['final_attack']
        total_a = status_a['total']
        total_b = status_b['total']

        efficiency_a = (final_attack_a / total_a * 100) if total_a > 0 else 0
        efficiency_b = (final_attack_b / total_b * 100) if total_b > 0 else 0

        more_effective = team_a_name if final_attack_a >= final_attack_b else team_b_name
        more_efficient = team_a_name if efficiency_a >= efficiency_b else team_b_name

        insights = []
        if final_attack_a > final_attack_b:
            insights.append(f"**{team_a_name} was more effective** - reached final attack {final_attack_a - final_attack_b} more times")
        elif final_attack_b > final_attack_a:
            insights.append(f"**{team_b_name} was more effective** - reached final attack {final_attack_b - final_attack_a} more times")
        else:
            insights.append("**Both teams were equally effective** - reached final attack the same number of times")

        if efficiency_a > efficiency_b:
            insights.append(f"**{team_a_name} was more efficient** - {efficiency_a:.1f}% vs {efficiency_b:.1f}%")
        elif efficiency_b > efficiency_a:
            insights.append(f"**{team_b_name} was more efficient** - {efficiency_b:.1f}% vs {efficiency_a:.1f}%")

        if counts_a['build_up'] > counts_b['build_up']:
            insights.append(f"**{team_a_name}** focused more on build-up play ({counts_a['build_up']} vs {counts_b['build_up']})")
        elif counts_b['build_up'] > counts_a['build_up']:
            insights.append(f"**{team_b_name}** focused more on build-up play ({counts_b['build_up']} vs {counts_a['build_up']})")

        return f"""**Team Comparison - Performance Analysis**

| Phase | {team_a_name} | {team_b_name} |
|-------|---------------|---------------|
| Build Up | {counts_a['build_up']} | {counts_b['build_up']} |
| Progression | {counts_a['progression']} | {counts_b['progression']} |
| Final Attack | {counts_a['final_attack']} | {counts_b['final_attack']} |
| **Total** | **{total_a}** | **{total_b}** |
| **Attack Efficiency** | **{efficiency_a:.1f}%** | **{efficiency_b:.1f}%** |

**Key Insights:**
{chr(10).join(f"- {insight}" for insight in insights)}

**Summary:**
{more_effective} reached final attacking positions more effectively, while {more_efficient} converted phases into attacks more efficiently."""

    def _format_comparison_formation(self, team_a: str, team_b: str, phase: str, form_a: Dict, form_b: Dict, mode: str) -> str:
        """Format formation comparison."""
        team_a_name = self._display_team_name(team_a)
        team_b_name = self._display_team_name(team_b)
        phase_name = phase.replace('_', ' ').title()
        
        if not form_a or not form_b:
            return "Formation data not available for comparison."
        
        return f"""**Formation Comparison - {phase_name} Phase ({mode.title()})**

| Metric | {team_a_name} | {team_b_name} |
|--------|---------------|---------------|
| Formation | {form_a['formation']} | {form_b['formation']} |
| Structure | {'-'.join(map(str, form_a['formation_tuple']))} | {'-'.join(map(str, form_b['formation_tuple']))} |
| Frames | {form_a['frames_count']} | {form_b['frames_count']} |
| Avg Players | {form_a['avg_outfield_count']:.1f} | {form_b['avg_outfield_count']:.1f} |"""
    
    def _format_comparison_all_formations(self, team_a: str, team_b: str, mode: str) -> str:
        """Format comparison of all formations."""
        team_a_name = self._display_team_name(team_a)
        team_b_name = self._display_team_name(team_b)
        
        lines = [f"**Formation Comparison - All Phases ({mode.title()})**\n"]
        
        for phase in ['build_up', 'progression', 'final_attack']:
            form_a = self.get_formation(team_a, phase, mode)
            form_b = self.get_formation(team_b, phase, mode)
            phase_name = phase.replace('_', ' ').title()
            
            if form_a and form_b:
                lines.append(f"\n**{phase_name}:**")
                lines.append(f"- {team_a_name}: {form_a['formation']}")
                lines.append(f"- {team_b_name}: {form_b['formation']}")
        
        return '\n'.join(lines)
    
    def _get_help_message(self) -> str:
        """Return help message."""
        return """**Team Analytics Bot - How to Ask Questions**

I can understand various ways of asking! Here are examples:

**Team Status:**
- "What is the status of Team A?"
- "How many phases for Team W?"
- "Show me Team A statistics"
- "Tell me about Team W"

**Formations:**
- "What formation does Team A use in progression?"
- "Show me Team W's formations"
- "What's the tactical setup for Team A?"
- "How is Team W setup in build up?"

**Line Positions:**
- "Where was the back line when Team A was attacking?"
- "What was the defensive line position in final attack?"
- "Show midfield line positions for Team A"
- "Where were the forwards positioned?"
- "Tell me about the line positions"

**Shape & Metrics:**
- "What was Team W's shape in build up?"
- "Show shape metrics for Team A final attack"
- "How wide was Team A in progression?"

**Comparisons:**
- "Compare Team A and Team W"
- "Who had more phases?"
- "Show me the difference between teams"

**Coach Summary Mode:**
- "coach summary liverpool"
- "coach mode for Team A"
- "give me coaching report for Team W"
- "training focus for liverpool"

**Available:** Team A, Team W | Phases: build up, progression, final attack | Modes: attack (default) or defense

**Tip:** You can ask follow-up questions without repeating the team name!"""

    def _format_passing_relations(self, team: str) -> str:
        """Format passing relations data for display."""
        team_key = team.lower().replace(' ', '_')
        # Handle the case where team might be "team_w" but data keys are "team_W"
        if team_key not in self.pass_relations:
            # Try with original case
            if team in self.pass_relations:
                team_key = team
            # Try uppercase version
            elif team_key.upper() in self.pass_relations:
                team_key = team_key.upper()
        
        if team_key not in self.pass_relations:
            return f"No passing data found for {team}."
        
        pass_data = self.pass_relations[team_key]
        team_name = self._display_team_name(team)
        
        # Extract metadata
        meta = pass_data.get('meta', {})
        num_relations = meta.get('num_relations', 'Unknown')
        pitch_blocks = meta.get('pitch_blocks', 'Unknown')
        action_type = meta.get('action_type', 'pass')
        stage_groups = meta.get('stage_groups', [])
        
        # Count blocks with data
        blocks = pass_data.get('blocks', {})
        active_blocks = len([k for k, v in blocks.items() if v.get('received', {}).get('total', 0) > 0])
        
        return f"""**{team_name} Passing Relations**

**Data Overview:**
- Total Pass Relations: {num_relations}
- Active Pitch Blocks: {active_blocks} of {pitch_blocks}
- Action Type: {action_type.title()}
- Stages: {', '.join(stage_groups)}

**Passing Network Analysis:**
- Player-to-player connections across {pitch_blocks} pitch zones
- Pass frequency and direction patterns
- Team passing structure by stage

**Available for detailed queries:**
- Pass completion rates by zone
- Key passing partnerships
- Passing patterns by stage (Build-Up, Progression, Final Attack)
- Zone-to-zone passing networks"""

    def _format_pass_direction(self, team: str, direction: str) -> str:
        """Format directional pass counts."""
        counts = self._get_pass_direction_counts(team)
        team_name = self._display_team_name(team)
        if not counts:
            return f"No passing data found for {team_name}."

        dir_counts = counts.get(direction, {'total': 0, 'success': 0, 'fail': 0})
        total_passes = sum(v['total'] for v in counts.values())
        share = (dir_counts['total'] / total_passes * 100.0) if total_passes else 0.0

        return f"""**{team_name} {direction.title()} Passes**

- Total {direction} passes created: {dir_counts['total']}
- Successful: {dir_counts['success']}
- Failed: {dir_counts['fail']}
- Share of all recorded passes: {share:.1f}%

Directional counts are computed from stage transitions (higher stage = forward, lower = backward, equal = lateral)."""

    def _format_dribbling_relations(self, team: str) -> str:
        """Format dribbling relations data for display."""
        team_key = team.lower().replace(' ', '_')
        # Handle the case where team might be "team_w" but data keys are "team_W"
        if team_key not in self.dribble_relations:
            # Try with original case
            if team in self.dribble_relations:
                team_key = team
            # Try uppercase version
            elif team_key.upper() in self.dribble_relations:
                team_key = team_key.upper()
        
        if team_key not in self.dribble_relations:
            return f"No dribbling data found for {team}."
        
        dribble_data = self.dribble_relations[team_key]
        team_name = self._display_team_name(team)
        
        # Extract metadata
        meta = dribble_data.get('meta', {})
        num_relations = meta.get('num_relations', 'Unknown')
        pitch_blocks = meta.get('pitch_blocks', 'Unknown')
        action_type = meta.get('action_type', 'dribble')
        stage_groups = meta.get('stage_groups', [])
        
        # Count blocks with data
        blocks = dribble_data.get('blocks', {})
        active_blocks = len([k for k, v in blocks.items() if v.get('received', {}).get('total', 0) > 0])
        
        return f"""**{team_name} Dribbling Relations**

**Data Overview:**
- Total Dribble Relations: {num_relations}
- Active Pitch Blocks: {active_blocks} of {pitch_blocks}
- Action Type: {action_type.title()}
- Stages: {', '.join(stage_groups)}

**Dribbling Network Analysis:**
- Player dribbling attempts across {pitch_blocks} pitch zones
- Dribble success rates by area
- Team dribbling patterns by stage
- Key dribblers and their impact zones

**Available for detailed queries:**
- Dribble completion rates by zone
- Key dribbling partnerships
- Dribbling patterns by stage (Build-Up, Progression, Final Attack)
- Individual player dribbling statistics
- Zone-to-zone dribbling networks"""


def main():
    """Run the interactive chatbot."""
    print("=" * 60)
    print("TEAM ANALYTICS CHATBOT MVP - ENHANCED")
    print("=" * 60)
    print("\nAsk me about Team A or Team W:")
    print("- Natural language questions supported!")
    print("- Try: 'Where was Team A back line in progression?'")
    print("- Try: 'Compare both teams'")
    print("- Try: 'What formations did Team W use?'")
    print("\nType 'help' for examples or 'quit' to exit.\n")
    
    # Initialize bot
    data_path = r'C:\Users\mahmo\Downloads\MVP\team_shape_summary.json'
    bot = TeamAnalyticsBot(data_path)
    
    while True:
        try:
            question = input("\nYou: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            answer = bot.answer_question(question)
            print(f"\nBot:\n{answer}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
