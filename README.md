# Connectara Backend 🧠

Connectara is an intelligent, agentic backend for social networking that leverages Graph RAG, Personality AI, and Real-Time Event Processing to create meaningful connections.

## 🚀 Features

### 1. **Hybrid Matching Engine** 🧬
-   **Content-Based Matching**: Generates semantic embeddings (using `all-MiniLM-L6-v2`) from user summaries and posts to find people with similar interests.
-   **Personality Compatibility**: Re-ranks matches using a heuristic algorithm based on Big Five (OCEAN) personality traits derived from text analysis (using `Minej/bert-base-personality`).

### 2. **Real-Time Social Graph** 🕸️
-   **Event-Driven Architecture**: Consumes message events from Kafka in real-time.
-   **Sentiment Analysis**: Analyzes the sentiment of every interaction using `distilbert-base-uncased-finetuned-sst-2-english`.
-   **Dynamic Relationships**: Updates the Neo4j graph with weighted `INTERACTED_WITH` relationships that track message count, last interaction time, and average sentiment.

### 3. **Autonomous Discovery & Retrieval** 🕵️‍♂️
-   **Smart Discovery**: Uses **SerpApi** (Google Search) to find LinkedIn posts and articles for a given user.
-   **Intelligent Crawling**: Uses **Playwright** to scrape content, handling dynamic rendering and specific LinkedIn HTML structures.
-   **Profile Enrichment**: Integrates with **Piloterr** to fetch structured LinkedIn profile data.

### 4. **Clean Architecture & Modern Stack** 🏗️
-   **Framework**: FastAPI (Python 3.11).
-   **Database**: Neo4j (Graph + Vector Index).
-   **Messaging**: Kafka (Confluent Cloud) + Series API.
-   **Containerization**: Docker & Docker Compose with optimized build caching (pre-loaded AI models).

---

## 🛠️ Architecture

The project follows **Clean Architecture** principles to ensure separation of concerns:

-   **`app/domain`**: Core business entities (`Person`, `AnalysisJob`) and abstract ports (`SocialGraph`, `MessagingService`).
-   **`app/use_cases`**: Application logic (`AnalyzeProfileUseCase`, `FindMatchesUseCase`, `ReceiveMessageUseCase`).
-   **`app/infrastructure`**: External adapters (`Neo4jAdapter`, `SerpApiDiscoveryAdapter`, `KafkaEventConsumer`, `BertAdapter`).
-   **`app/interfaces`**: Entry points (`api.py` for REST, `main.py` for CLI/Workers).

---

## ⚡️ Setup & Installation

### Prerequisites
-   Docker & Docker Compose
-   Neo4j (Running via Docker)
-   API Keys (See Configuration)

### 1. Configuration
Create a `.env` file in the root directory:

```env
# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# APIs
SERP_TOKEN=your_serpapi_key
PILOTERR_API_KEY=your_piloterr_key
GOOGLE_API_KEY=your_google_key (Optional fallback)
SEARCH_ENGINE_ID=your_cx_id (Optional fallback)

# Messaging (Series & Kafka)
SERIES_API_BASE_URL=https://series-hackathon-service-202642739529.us-east1.run.app
SERIES_API_KEY=your_series_key
SERIES_SENDER_NUMBER=your_sender_number

KAFKA_BOOTSTRAP_SERVERS=your_broker_url
KAFKA_TOPIC=your_topic
KAFKA_API_KEY=your_kafka_key
KAFKA_API_SECRET=your_kafka_secret
```

### 2. Run with Docker
This command will build the image (downloading AI models) and start the services.

```bash
docker compose up --build
```

---

## 🧪 How to Test

### 1. Analyze a Profile (Hybrid Matching)
Trigger the analysis pipeline to fetch a profile, crawl posts, analyze personality, and find matches.

**Request:**
```bash
curl -X POST "http://localhost:8000/analyze" \
     -H "Content-Type: application/json" \
     -d '{"username": "linkedin_username"}'
```

**Verification:**
1.  Check the logs: You should see "Fetching profile...", "Discovering posts...", "Analyzing personality...", "Finding matches...".
2.  Check Neo4j Browser (`http://localhost:7474`):
    ```cypher
    MATCH (p:Person {username: "linkedin_username"})
    RETURN p.ocean_vector, p.content_embedding, p.personality_analysis
    ```

### 2. Real-Time Messaging & Graph
Send a message to the Kafka topic (simulating an incoming SMS/WhatsApp).

**Simulate Event (Python Script):**
You can use a simple script to produce a message to your Kafka topic:

```json
{
  "event_type": "message.received",
  "data": {
    "chat_id": "test_chat_123",
    "text": "I really enjoyed our conversation today! Let's collaborate.",
    "from_phone": "+1234567890",
    "chat_handles": [{"identifier": "+1234567890", "is_me": false}]
  }
}
```

**Verification:**
1.  **Logs**: The app should log "Received message...", "Sentiment Score: 0.99" (Positive).
2.  **Reply**: The bot should reply via Series API (check logs for "Sent reply").
3.  **Graph Update**: Check Neo4j for the relationship:
    ```cypher
    MATCH (a:Person {username: "+1234567890"})-[r:INTERACTED_WITH]->(b)
    RETURN r.weight, r.avg_sentiment, r.last_interaction
    ```
    Send another message (e.g., "This is bad") and watch `r.weight` increase and `r.avg_sentiment` drop.

---

## 📂 Project Structure

```
.
├── app/
│   ├── domain/         # Entities & Ports
│   ├── use_cases/      # Business Logic
│   ├── infrastructure/ # Adapters (Neo4j, AI, APIs)
│   ├── interfaces/     # FastAPI Routes
│   └── containers.py   # Dependency Injection
├── neo4j/              # Database Data
├── Dockerfile          # Optimized Build
├── docker-compose.yml  # Service Orchestration
├── requirements.txt    # Light Dependencies
├── requirements-core.txt # Heavy Dependencies (Cached)
└── download_models.py  # Model Pre-loader
```
