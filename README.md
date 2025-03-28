# TV Series Recommender

A chatbot that helps users discover TV series based on their preferences using the TVDB API and OpenAI's LLM for natural language understanding.

## Features

- Natural language understanding of user queries about TV series
- Maintains conversational context for follow-up questions
- Provides personalized TV series recommendations based on user preferences
- Sources all information directly from the TVDB API for accurate recommendations
- FastAPI-based web interface for easy interaction

## Setup

### Prerequisites

- Python 3.8 or higher
- TVDB API key 
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tv-series-recommender.git
cd tv-series-recommender
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your API keys:
```
TVDB_API_KEY=your_tvdb_api_key
TVDB_PIN=your_tvdb_pin_if_needed
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
```

### Running the Application

```bash
python run.py
```

The application will be available at http://127.0.0.1:8000

## Usage

1. Open your browser and navigate to http://127.0.0.1:8000
2. Type your queries in natural language in the chat interface
3. The bot will use LLM to understand your query and respond with relevant TV series recommendations based on your preferences

## Example Queries

- "I like sci-fi shows like Star Trek. What should I watch next?"
- "Tell me about Breaking Bad"
- "What are some popular shows on HBO?"
- "What similar shows are there to Stranger Things?"
- "I enjoy dramas with strong female leads. Any recommendations?"

## Architecture

The application is structured into the following components:

- **FastAPI Application**: Handles HTTP requests and responses
- **TVDB Client**: Makes API calls to the TVDB API to fetch TV series data
- **LLM Service**: Uses OpenAI's API to understand natural language queries
- **Conversation Memory**: Maintains conversation context for better user experience
- **Chatbot**: Orchestrates all components to provide a seamless experience

## API Endpoints

- `GET /`: Web interface for the chatbot
- `POST /api/chat`: Send a message to the chatbot
- `GET /api/search/{query}`: Search for TV series by name
- `GET /api/series/{series_id}`: Get details about a specific TV series
- `GET /api/similar/{series_id}`: Get similar TV series recommendations
- `GET /api/health`: Health check endpoint

## Customization

- Change the LLM model by updating the `OPENAI_MODEL` in your `.env` file
- Adjust conversation memory settings in `app/chatbot/memory.py`
- Customize the UI in `app/templates/index.html`

## License

MIT