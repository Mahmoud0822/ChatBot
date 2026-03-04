"""
Enhanced Team Analytics Bot with optional OpenAI integration
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EnhancedTeamAnalyticsBot:
    def __init__(
        self,
        data_path: str,
        use_llm: bool = False,
        match_metadata_path: Optional[str] = None,
        team_mapping_path: Optional[str] = None,
    ):
        """Initialize bot with team data and optional LLM."""
        with open(data_path, "r") as f:
            self.data = json.load(f)
        self.stage_counts = self.data["stage_counts"]
        self.summary = self.data["summary"]
        self.conversation_context = {}

        # Load pass and dribble relations data
        base_dir = os.path.dirname(data_path)
        self.pass_relations = {}
        self.dribble_relations = {}

        for team in ["team_A", "team_W"]:
            pass_file = os.path.join(base_dir, f"{team}_pass_relations.json")
            dribble_file = os.path.join(base_dir, f"{team}_dribble_relations.json")

            if os.path.exists(pass_file):
                with open(pass_file, "r") as f:
                    self.pass_relations[team] = json.load(f)

            if os.path.exists(dribble_file):
                with open(dribble_file, "r") as f:
                    self.dribble_relations[team] = json.load(f)

        # Keep a single rule-based bot instance to preserve conversation context.
        from team_analytics_bot import TeamAnalyticsBot

        self.rule_bot = TeamAnalyticsBot(
            data_path,
            match_metadata_path=match_metadata_path,
            team_mapping_path=team_mapping_path,
        )

        # LLM setup (optional)
        self.use_llm = use_llm
        self.llm_available = False
        self.client = None
        self._setup_llm_client()

    def _setup_llm_client(self) -> None:
        """Initialize OpenAI client if available in environment."""
        try:
            from openai import OpenAI
        except ImportError:
            print("Warning: OpenAI library not installed. Run: pip install openai")
            self.use_llm = False
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found in .env file. LLM mode unavailable.")
            self.use_llm = False
            return

        self.client = OpenAI(api_key=api_key)
        self.llm_available = True
        if self.use_llm:
            print("OpenAI LLM enabled for enhanced responses")

    def _enhance_with_llm(self, question: str, rule_based_response: str) -> str:
        """Enhance rule-based response with LLM for more natural language."""
        if not self.llm_available:
            return rule_based_response

        try:
            prompt = f"""
            You are a football analytics assistant. The user asked: "{question}"

            The rule-based system provided this data-driven response:
            {rule_based_response}

            Please enhance this response to be more natural and conversational while keeping all factual data intact.
            Keep the same structure and information but make it sound more like a knowledgeable football analyst.
            Do not add any information that wasn't in the original response.
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"LLM error: {e}. Falling back to rule-based response.")
            return rule_based_response

    def answer_question(self, question: str, use_llm: Optional[bool] = None) -> str:
        """Answer a question using rule-based system with optional LLM enhancement."""
        rule_based_response = self.rule_bot.answer_question(question)

        # Resolve effective mode: explicit override if provided, otherwise default instance mode.
        should_use_llm = self.use_llm if use_llm is None else use_llm
        if should_use_llm and self.llm_available:
            return self._enhance_with_llm(question, rule_based_response)

        return rule_based_response


if __name__ == "__main__":
    # Test enhanced bot
    data_path = os.path.join(os.path.dirname(__file__), "team_shape_summary.json")

    print("Choose mode:")
    print("1. Rule-based only (fast, free)")
    print("2. Enhanced with LLM (natural responses)")

    choice = input("Enter choice (1 or 2): ").strip()

    use_llm = choice == "2"
    bot = EnhancedTeamAnalyticsBot(data_path, use_llm=use_llm)

    print("\nEnhanced Team Analytics Bot ready!")
    print("Ask questions about teams, formations, passing, dribbling, etc.")
    print("Type 'quit' to exit\n")

    while True:
        question = input("You: ").strip()
        if question.lower() == "quit":
            break

        response = bot.answer_question(question)
        print(f"Bot: {response}\n")
