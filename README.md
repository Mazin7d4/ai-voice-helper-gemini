# AI Voice Helper MVP

A simple UI navigation agent that uses Gemini AI to control a web browser through screenshots and actions.

## Features

- **Screenshot-based navigation**: Takes screenshots of web pages and sends them to Gemini AI
- **JSON action responses**: Gemini returns structured actions (click, type, scroll, done)
- **Playwright automation**: Executes actions in a real browser
- **Loop-based interaction**: Continues navigating until goal is complete or max steps reached

## Setup

### Prerequisites

- Python 3.8+
- Google Cloud Project with Vertex AI enabled
- Service account key with Vertex AI permissions

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-voice-helper
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m playwright install
   ```

4. **Configure environment**
   - Copy `.env` and update with your values:
   ```env
   GCP_PROJECT_ID=your-project-id
   GCP_LOCATION=us-central1
   GEMINI_MODEL=gemini-2.5-flash
   START_URL=https://example.com
   ```

5. **Set up Google Cloud credentials**
   ```bash
   # Set the path to your service account key
   setx GOOGLE_APPLICATION_CREDENTIALS "path/to/your/service-account-key.json"
   ```

### Google Cloud Setup

1. **Enable APIs** in your Google Cloud project:
   - Vertex AI API
   - Generative Language API

2. **Create a service account** with Vertex AI User role

3. **Download the service account key** JSON file

## Usage

Run the demo:
```bash
python -m app.main
```

Enter a goal like:
- "Click the first link"
- "Scroll down"
- "Tell me what this website is"

The agent will:
1. Open a browser to the start URL
2. Take a screenshot
3. Send screenshot + goal to Gemini
4. Execute the returned action
5. Repeat until done or max steps reached

## Project Structure

```
ai-voice-helper/
├── app/
│   ├── __init__.py
│   ├── main.py          # Entry point and loop
│   ├── gemini.py        # Gemini AI integration
│   └── browser.py       # Playwright browser control
├── requirements.txt     # Python dependencies
├── .env                 # Environment configuration
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Architecture

- **app/main.py**: Orchestrates the loop - screenshot → Gemini → action → repeat
- **app/gemini.py**: Handles Vertex AI integration with structured JSON responses
- **app/browser.py**: Playwright wrapper for screenshot and action execution

## Models

Currently using `gemini-2.5-flash` via Vertex AI. The system prompt instructs Gemini to return actions in this JSON format:

```json
{
  "type": "click|type|scroll|done",
  "target_text": "string",
  "text": "string",
  "scroll": {"direction": "down|up", "amount": 1},
  "explanation": "string"
}
```

## Future Enhancements

- Voice input/output
- More sophisticated action types
- Error handling and retries
- Multi-page navigation
- Goal completion detection

## License

MIT License