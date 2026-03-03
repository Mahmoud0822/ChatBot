"""
Team Analytics Chatbot MVP - Flask Web Server
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from enhanced_bot import EnhancedTeamAnalyticsBot

app = Flask(__name__)

# Initialize enhanced bot - set use_llm=False to disable LLM if API key issues
DATA_PATH = os.path.join(os.path.dirname(__file__), 'team_shape_summary.json')
MATCH_METADATA_PATH = os.path.join(os.path.dirname(__file__), 'match_metadata.json')
TEAM_MAPPING_PATH = os.path.join(os.path.dirname(__file__), 'team_mapping.json')
USE_LLM = False  # Keep deterministic analytics answers by default
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
        
        if not message:
            return jsonify({'response': 'Please enter a message.'})
        
        # Get response from bot
        response = bot.answer_question(message)
        
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'response': f'Sorry, an error occurred: {str(e)}'}), 500

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'data_loaded': bot.data is not None})

if __name__ == '__main__':
    print("=" * 60)
    print("Team Analytics Chatbot MVP - Starting Server")
    print("=" * 60)
    print("\nOpen your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
