# Poppy Ideation

A collaborative idea management platform built with Streamlit and Supabase.

## Setup

1. Create a `.env` file in the project root with the following variables:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
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

- Create and manage ideas with titles, descriptions, and context
- Categorize ideas with status, priority, and categories
- Add tags to ideas for better organization
- Comment on ideas
- Filter ideas by status, priority, and category
- Modern, user-friendly interface

## Deployment

To deploy this app to Streamlit Sharing:

1. Create a GitHub repository and push your code
2. Go to [Streamlit Sharing](https://share.streamlit.io/)
3. Click "New App" and connect your GitHub account
4. Select your repository
5. The app will be automatically deployed and accessible via a public URL

## Environment Variables

Create a `.env` file with your Supabase credentials:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```
