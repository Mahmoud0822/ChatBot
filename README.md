# Team Analytics Chatbot MVP - Enhanced Version

An intelligent, natural language chatbot for analyzing football team data including formations, line positions, and match statistics. **Now handles ANY question you ask!**

## 🌟 Key Features

### 🧠 **Advanced Natural Language Understanding**
- Understands various ways of asking the same question
- Handles typos and informal language
- Context-aware follow-up questions
- No need to memorize specific phrases!

### 📊 **Comprehensive Data Analysis**
- **Team Status**: Phase counts and performance overview
- **Formations**: Tactical setups across all phases
- **Line Positions**: Defensive, midfield, and attacking lines
- **Shape Metrics**: Width, depth, spread, and stretch analysis
- **Comparisons**: Team A vs Team W analysis

### 💬 **Question Types Supported**

**Status & Overview:**
- "What is the status of Team A?"
- "Tell me about Team W"
- "How did team a perform?"
- "Show me the statistics"

**Formations:**
- "What formation does Team A use?"
- "What's the tactical setup?"
- "Show me all formations"
- "How is Team W setup in build up?"

**Line Positions:**
- "Where was the back line?"
- "Show me defensive line positions"
- "Where were the midfielders?"
- "What about the attacking line?"

**Shape & Metrics:**
- "What was Team W's shape in progression?"
- "How wide was the team?"
- "Show shape metrics"

**Comparisons:**
- "Compare both teams"
- "Who attacked more?"
- "Which team is better?"
- "What's the difference?"

**Comprehensive:**
- "Tell me everything about Team A in build up"
- "Show me all data"

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run the Web Application
```bash
python app.py
```

Then open: **http://localhost:5000**

### Or use the Launcher (Windows)
Double-click `start_bot.bat`

## 💡 Usage Examples

### Example 1: Simple Status Query
```
You: What is the status of Team A?
Bot: **Team A Status**
     - Build Up: 15 phases
     - Progression: 8 phases
     - Final Attack: 6 phases
     - Total: 29 phases
```

### Example 2: Formation Query
```
You: What formation does Team W use in progression?
Bot: **Team W - Progression Phase**
     Formation: 2-4-4
     Frames Analyzed: 235
     Average Outfield Players: 10.0
```

### Example 3: Natural Language Line Query
```
You: Where was the back line when Team A was attacking?
Bot: **Team A Defensive Line Positions (Attack)**
     Build Up: Position X = 18.1m, Width = 22.9m
     Progression: Position X = 39.2m, Width = 20.4m
     Final Attack: Position X = 60.7m, Width = 16.2m
```

### Example 4: Comparison
```
You: Compare both teams
Bot: **Team Comparison - Phase Counts**
     | Phase | Team A | Team W |
     |-------|--------|--------|
     | Build Up | 15 | 10 |
     | Progression | 8 | 21 |
     | Final Attack | 6 | 21 |
     | Total | 29 | 52 |
     
     Analysis: Team W had more attacking phases
```

### Example 5: Follow-up Question (Context-Aware)
```
You: What is the status of Team A?
Bot: [Shows Team A status]

You: What about their formations?
Bot: [Shows Team A formations - no need to repeat "Team A"!]
```

## 🎯 Natural Language Features

### Handles Variations
✅ "Whats the setup for Team A?"  
✅ "how did team a perform?"  
✅ "Team W defensive line final attack"  
✅ "where are the defenders"  
✅ "who attacked more?"

### Context Awareness
✅ Follow-up questions without repeating team names  
✅ Remembers previous context  
✅ Smart defaults (shows all phases if not specified)

### Typos & Informal Language
✅ "team a" vs "Team A"  
✅ "Whats" instead of "What's"  
✅ "vs" instead of "versus"  
✅ Missing punctuation

## 📁 Project Structure

```
MVP/
├── app.py                      # Flask web server
├── team_analytics_bot.py       # Core bot logic (ENHANCED)
├── templates/
│   └── index.html             # Web interface
├── requirements.txt            # Python dependencies
├── start_bot.bat              # Windows launcher
├── README.md                  # This file
├── BOT_CAPABILITIES.md        # Detailed capabilities
└── team_shape_summary.json    # Your data file
```

## 🔧 Technical Details

### Intent Detection
The bot uses pattern matching with regex to detect:
- **10 different intents**: status, formation, defensive_line, midfield_line, attacking_line, all_lines, shape, comparison, help, unknown
- **Scoring system**: Multiple patterns can match, highest score wins
- **Flexible patterns**: Each intent has 5-10 different ways to express it

### Entity Extraction
Automatically extracts:
- **Team**: Team A, Team W (with fuzzy matching)
- **Phase**: build_up, progression, final_attack (with pattern variations)
- **Mode**: attack (default) or defense

### Context Management
- Maintains conversation history
- Remembers last mentioned team
- Supports pronoun references ("they", "their", "them")

### Smart Defaults
- If no phase specified → shows all phases
- If no team specified → uses context or asks user
- If unclear intent → provides helpful summary

## 📊 Data Structure

The bot queries `team_shape_summary.json` which contains:
- **stage_counts**: Phase entry counts for each team
- **summary**: Detailed analytics including:
  - Formations (e.g., "2-4-4", "3-4-3")
  - Line positions (defensive, midfield, attacking)
  - Shape metrics (width, depth, spread, stretch)
  - Frame-by-frame player positions

## 🎨 Web Interface Features

- **Modern, responsive design**
- **Typing indicator** while processing
- **Suggestion chips** for quick queries
- **Beautiful formatting** with markdown support
- **Mobile-friendly** layout

## 🛠️ Advanced Usage

### Custom Questions
You can ask questions in almost any way:
- Formal: "What is the formation of Team A in the progression phase?"
- Informal: "Whats Team A setup in progression?"
- Short: "Team A formation progression"
- Natural: "How did Team A setup their formation when progressing?"

### Comparison Queries
The bot can compare teams on:
- Total phases
- Individual phase counts
- Formations
- Line positions
- Shape metrics

### Comprehensive Views
Ask for "everything" to get:
- Formation
- All line positions
- Shape metrics
- In a single response

## 📝 Example Conversation

```
You: Tell me about Team W
Bot: [Shows Team W summary with 52 total phases]

You: What formation did they use?
Bot: [Shows all Team W formations]

You: Where was their back line in progression?
Bot: [Shows defensive line position]

You: Compare them to Team A
Bot: [Shows detailed comparison]

You: Who attacked more?
Bot: Team W had more attacking phases (52 vs 29)
```

## 🤝 Contributing

Feel free to enhance the bot by:
- Adding more question patterns
- Improving intent detection
- Adding visualization features
- Extending data analysis capabilities

## 📄 License

This MVP is built for demonstration purposes.

---

**Ready to chat?** Run `python app.py` and start asking questions! 🚀
