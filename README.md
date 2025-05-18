# Poppy Ideation

A collaborative idea management platform built with Streamlit and Supabase, featuring AI-powered ranking and sprint management capabilities.

## Setup

1. Create a `.env` file in the project root with the following variables:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_api_key
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   streamlit run app_enhanced.py
   ```

## Features

- **Idea Management**
  - Create new ideas with titles, descriptions, sources, and context
  - Assign categories, priorities, and statuses
  - Add multiple tags for organization
  - View and edit idea rankings
  - Delete ideas
  - Promote ideas to "In Progress" status
  - AI-powered ranking system

- **Sprint Management**
  - Track sprint status (active, upcoming, completed)
  - View sprint metrics (points, velocity)
  - Manage sprint backlog items
  - Track sprint progress

- **User Interface**
  - Clean, intuitive interface for managing ideas and sprints
  - Real-time filtering by status, priority, and category
  - Checkbox selection for bulk actions
  - Responsive design for all screen sizes

- **Data Management**
  - Supabase backend for data storage
  - Real-time updates across all views
  - Automatic timestamp tracking
  - User authentication support

## Technical Details

- **Architecture**
  - Frontend: Streamlit
  - Backend: Supabase
  - AI: OpenAI API
  - Database: PostgreSQL (via Supabase)

- **Data Schema**
  - Ideas table with fields for title, description, rank, status, priority, category
  - Status tracking system
  - Priority levels
  - Category system
  - Tagging system with many-to-many relationships
  - Sprint management tables
  - Timestamp tracking

## Current Development Status

The application is actively being developed with ongoing improvements to the sprint management system and idea ranking functionality. The current focus is on:
- Sprint metrics tracking
- Idea status management
- Bulk action capabilities
- UI/UX enhancements

## Deployment

To deploy this app to Streamlit Sharing:

1. Create a GitHub repository and push your code
2. Go to [Streamlit Sharing](https://share.streamlit.io/)
3. Click "New App" and connect your GitHub account
4. Select your repository
5. Configure environment variables in Streamlit Cloud
6. The app will be automatically deployed and accessible via a public URL

## Environment Variables

Create a `.env` file with your credentials:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
```

## AI & RAG Setup

To enable AI-powered features (like idea re-ranking, summarization, or retrieval-augmented generation), you must add your API keys to Streamlit secrets:

1. In your `.streamlit/secrets.toml` (or via Streamlit Cloud secrets UI), add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   VECTOR_DB_API_KEY = "your_vector_db_key"  # Optional, for RAG features
   ```
2. The app will show a badge in the sidebar if AI and RAG features are enabled.
3. If the OpenAI key is missing, AI features will be disabled and a warning will be shown.

**Note:** Some features (like AI re-ranking) require the OpenAI key. RAG features may require a vector DB key (e.g., Pinecone, Weaviate, Supabase vector, etc.).

## Contributing

(To be added: Guidelines for how others can contribute to this project. Consider creating a `CONTRIBUTING.md` file.)

## License

(To be added: Specify the license under which this project is shared. For example, MIT, Apache 2.0, etc. Consider creating a `LICENSE.md` file.)
