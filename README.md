# Poppy Ideation

A collaborative idea management platform built with Streamlit and Supabase, featuring AI-powered ranking and management capabilities.

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

- **AI Integration**
  - AI-powered ranking system that evaluates ideas based on multiple factors
  - Automatic ranking of new ideas upon creation
  - Manual re-ranking capability using AI
  - Rank scores from 1-100 based on idea quality and potential

- **User Interface**
  - Clean, single-table view of all ideas
  - Real-time filtering by status, priority, and category
  - Drag-and-drop rank reordering
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
  - Timestamp tracking

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
