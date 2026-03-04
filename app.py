"""
Team Analytics Chatbot MVP - Flask Web Server
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from enhanced_bot import EnhancedTeamAnalyticsBot

app = Flask(__name__)

# Initialize enhanced bot with default mode.
DATA_PATH = os.path.join(os.path.dirname(__file__), 'team_shape_summary.json')
MATCH_METADATA_PATH = os.path.join(os.path.dirname(__file__), 'match_metadata.json')
TEAM_MAPPING_PATH = os.path.join(os.path.dirname(__file__), 'team_mapping.json')
USE_LLM = False  # Default mode for requests that don't explicitly set "mode"
bot = EnhancedTeamAnalyticsBot(
    DATA_PATH,
    use_llm=USE_LLM,
    match_metadata_path=MATCH_METADATA_PATH,
    team_mapping_path=TEAM_MAPPING_PATH,
)

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
        
        use_llm = mode == 'llm'
        response = bot.answer_question(message, use_llm=use_llm)

        # If user requested LLM but it's unavailable, provide a clear note.
        if use_llm and not bot.llm_available:
            response = f"{response}\n\n[Note] LLM mode is not available on this server. Showing rule-based response."
        
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'response': f'Sorry, an error occurred: {str(e)}'}), 500

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'data_loaded': bot.data is not None,
        'llm_available': bot.llm_available,
        'default_mode': 'llm' if bot.use_llm else 'rule',
    })

if __name__ == '__main__':
    print("=" * 60)
    print("Team Analytics Chatbot MVP - Starting Server")
    print("=" * 60)
    print("\nOpen your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
