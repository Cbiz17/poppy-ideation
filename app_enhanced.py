import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import uuid
import pandas as pd
import openai

# --- Page config
st.set_page_config(page_title="Poppy Ideation", layout="wide")

# Initialize OpenAI
openai.api_key = st.secrets.get("OPENAI_API_KEY", "NOT_FOUND")

# Function to get AI ranking score
def get_ai_ranking_score(idea):
    """
    Get an AI-assisted ranking score for an idea based on multiple factors
    """
    try:
        # Combine relevant fields into a prompt
        prompt = f"""
        Evaluate this idea and provide a ranking score from 1-100:
        Title: {idea['title']}
        Description: {idea['description']}
        Context: {idea['context']}
        Source: {idea['source']}
        
        Consider the following factors:
        1. Innovation potential
        2. Feasibility
        3. Impact potential
        4. Strategic alignment
        5. Resource requirements
        
        Provide only a number between 1 and 100.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert in idea evaluation and ranking."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=10
        )
        
        score = response.choices[0].message.content.strip()
        # Ensure we get a valid number
        try:
            score = int(score)
            if 1 <= score <= 100:
                return score
            return 50  # Default score if out of range
        except:
            return 50  # Default score if not a number
            
    except Exception as e:
        print(f"Error getting AI ranking: {str(e)}")
        return 50  # Default score on error

# --- Initialize Supabase client
try:
    # Get secrets
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "NOT_FOUND")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "NOT_FOUND")
    
    if SUPABASE_URL == "NOT_FOUND" or SUPABASE_KEY == "NOT_FOUND":
        st.error("Could not find Supabase credentials in secrets")
        st.stop()
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error loading secrets: {str(e)}")
    st.stop()

# --- Header
st.title("Poppy Ideation")
st.success("Streamlit is up and running!")

# --- Helper function to get name lookups
def get_lookup(table_name):
    items = supabase.table(table_name).select("id", "name").execute().data
    return {
        item['id']: item['name']
        for item in items
    }

category_lookup = get_lookup("categories")
priority_lookup = get_lookup("priorities")
status_lookup = get_lookup("statuses")

# --- Sidebar
with st.sidebar:
    st.header("Filters")
    
    # Status filter
    status_options = supabase.table("statuses").select("id", "name").execute().data
    # Filter out "blocked" status
    status_options = [s for s in status_options if s["name"] != "blocked"]
    status_ids = [s["id"] for s in status_options]
    selected_status = st.selectbox("Status", 
                                 [s["name"] for s in status_options],
                                 index=0)
    selected_status_id = next(s["id"] for s in status_options if s["name"] == selected_status)
    
    # Priority filter
    priority_options = supabase.table("priorities").select("id", "name").execute().data
    priority_ids = [p["id"] for p in priority_options]
    selected_priority = st.selectbox("Priority", 
                                   [p["name"] for p in priority_options],
                                   index=0)
    selected_priority_id = next(p["id"] for p in priority_options if p["name"] == selected_priority)
    
    # Category filter
    category_options = supabase.table("categories").select("id", "name").execute().data
    category_ids = [c["id"] for c in category_options]
    selected_category = st.selectbox("Category", 
                                   [c["name"] for c in category_options],
                                   index=0)
    selected_category_id = next(c["id"] for c in category_options if c["name"] == selected_category)

# --- Main Layout
# Create new idea section
with st.container():
    with st.form("new_idea", clear_on_submit=True):
        st.header("💡 Create New Idea")
        
        title = st.text_input("Title", placeholder="Enter a title for your idea")
        description = st.text_area("Description", placeholder="Describe your idea in detail")
        source = st.text_input("Source", placeholder="Where did this idea come from?")
        context = st.text_area("Context", placeholder="Any additional context or background")
        
        # Tags
        tags = st.multiselect("Tags", 
                            [t["name"] for t in supabase.table("tags").select("id", "name").execute().data])
        
        # Use CSS to style the submit button
        st.markdown("""
        <style>
        .stButton > button {
            background-color: #4a90e2;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            if not title:
                st.warning("Please enter a title!")
            else:
                # Create the idea
                new_idea = {
                    "title": title,
                    "description": description,
                    "category_id": selected_category_id,
                    "status_id": selected_status_id,
                    "priority_id": selected_priority_id,
                    "source": source,
                    "context": context,
                    "creator_id": st.session_state.user_id if "user_id" in st.session_state else None
                }
                
                try:
                    # Insert idea with initial rank (0)
                    new_idea["rank"] = 0  # Start with default rank
                    idea_response = supabase.table("poppy_ideas_v2").insert(new_idea).execute()
                    idea_id = idea_response.data[0]["id"]
                    
                    # Link tags
                    for tag_name in tags:
                        tag = supabase.table("tags").select("id").eq("name", tag_name).execute().data[0]
                        supabase.table("idea_tags").insert({"idea_id": idea_id, "tag_id": tag["id"]}).execute()
                    
                    # Get AI ranking for the new idea
                    try:
                        idea_data = idea_response.data[0]
                        ai_score = get_ai_ranking_score(idea_data)
                        supabase.table("poppy_ideas_v2").update({"rank": ai_score}).eq("id", idea_id).execute()
                    except Exception as e:
                        print(f"Error getting AI ranking for new idea: {str(e)}")
                    
                    st.success("Idea created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating idea: {str(e)}")

    # Add a separator
    st.markdown("---")

# Display filtered ideas based on sidebar
with st.container():
    st.header("🔍 Filtered Ideas")
    
    # Apply filters from sidebar
    query = supabase.table("poppy_ideas_v2").select("*")
    
    # Apply filters
    if selected_status_id:
        query = query.eq("status_id", selected_status_id)
    if selected_priority_id:
        query = query.eq("priority_id", selected_priority_id)
    if selected_category_id:
        query = query.eq("category_id", selected_category_id)
    
    filtered_ideas_response = query.execute()
    filtered_ideas = filtered_ideas_response.data
    
    if filtered_ideas:
        # Create a DataFrame for display
        df = pd.DataFrame(filtered_ideas)
        
        # Format the DataFrame
        formatted_filtered = df[['title', 'description', 'rank', 'status_id', 'priority_id', 'category_id', 'created_at']].copy()
        formatted_filtered.columns = ['Title', 'Description', 'Rank', 'Status', 'Priority', 'Category', 'Created At']
        
        # Replace IDs with names
        formatted_filtered['Status'] = formatted_filtered['Status'].map(status_lookup)
        formatted_filtered['Priority'] = formatted_filtered['Priority'].map(priority_lookup)
        formatted_filtered['Category'] = formatted_filtered['Category'].map(category_lookup)
        
        # Display the filtered ideas
        st.dataframe(formatted_filtered)
    else:
        st.info("No ideas match your filters!")

    # Add a separator
    st.markdown("---")

# Saved Ideas section
with st.container():
    st.header("📁 Saved Ideas")
    
    # Get all ideas with their rank and sort by rank descending
    ideas_response = supabase.table("poppy_ideas_v2").select("*").order("rank", desc=True).execute()
    ideas = ideas_response.data
    
    if ideas:
        # Create a DataFrame for display
        df = pd.DataFrame(ideas)
        
        # Format the DataFrame
        formatted_ideas = df[['title', 'description', 'rank', 'status_id', 'priority_id', 'category_id', 'created_at']].copy()
        formatted_ideas.columns = ['Title', 'Description', 'Rank', 'Status', 'Priority', 'Category', 'Created At']
        
        # Replace IDs with names
        formatted_ideas['Status'] = formatted_ideas['Status'].map(status_lookup)
        formatted_ideas['Priority'] = formatted_ideas['Priority'].map(priority_lookup)
        formatted_ideas['Category'] = formatted_ideas['Category'].map(category_lookup)
        
        # Display the ideas in a simple table
        st.dataframe(formatted_ideas)
        
        # Create a container for management buttons
        with st.container():
            # Add management buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Delete Selected Ideas", key="delete_button"):
                    try:
                        # Get selected ideas
                        selected_ideas = formatted_ideas[formatted_ideas['Select']].index
                        if len(selected_ideas) > 0:
                            # Delete each selected idea
                            for idx in selected_ideas:
                                supabase.table("poppy_ideas_v2").delete().eq("id", ideas[idx]['id']).execute()
                            st.success("Selected ideas deleted successfully!")
                            st.rerun()
                        else:
                            st.warning("Please select at least one idea to delete")
                    except Exception as e:
                        st.error(f"Error deleting ideas: {str(e)}")
            
            with col2:
                if st.button("Promote Selected Ideas", key="promote_button"):
                    try:
                        # Get selected ideas
                        selected_ideas = formatted_ideas[formatted_ideas['Select']].index
                        if len(selected_ideas) > 0:
                            # Promote each selected idea to "In Progress"
                            in_progress_id = next(s['id'] for s in status_options if s['name'] == "In Progress")
                            for idx in selected_ideas:
                                supabase.table("poppy_ideas_v2").update({"status_id": in_progress_id}).eq("id", ideas[idx]['id']).execute()
                            st.success("Selected ideas promoted to In Progress!")
                            st.rerun()
                        else:
                            st.warning("Please select at least one idea to promote")
                    except Exception as e:
                        st.error(f"Error promoting ideas: {str(e)}")
            
            with col3:
                if st.button("Re-Rank All Ideas with AI", key="re_rank_button"):
                    try:
                        # Get all ideas that need ranking
                        ideas_to_rank = supabase.table("poppy_ideas_v2").select("*").execute().data
                        
                        # Process each idea
                        for idea in ideas_to_rank:
                            # Get AI ranking score
                            score = get_ai_ranking_score(idea)
                            
                            # Update the idea's rank
                            supabase.table("poppy_ideas_v2").update({"rank": score}).eq("id", idea["id"]).execute()
                        
                        st.success("All ideas have been re-ranked using AI!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error re-ranking ideas: {str(e)}")
    else:
        st.info("No ideas found!")

    # Format ideas
    formatted_ideas = []
    for idea in ideas:
        formatted_ideas.append({
            "Title": idea["title"],
            "Description": idea["description"],
            "Source": idea["source"],
            "Context": idea["context"],
            "Category": category_lookup.get(idea["category_id"], "Unknown"),
            "Priority": priority_lookup.get(idea["priority_id"], "Unknown"),
            "Status": status_lookup.get(idea["status_id"], "Unknown"),
            "Created At": idea["created_at"][:10]  # just the date
        })

    # Display saved ideas with ranking and management
    if formatted_ideas:
        # Get all ideas with their rank
        all_ideas = supabase.table("poppy_ideas_v2").select("id", "title", "rank").execute().data
        
        # Create a DataFrame with an additional column for selection
        df = pd.DataFrame(formatted_ideas)
        df['Select'] = False  # Add a selection column
        df['Rank'] = [next((i['rank'] for i in all_ideas if i['title'] == row['Title']), 0) for _, row in df.iterrows()]
        
        # Add a button to re-rank all ideas using AI
        if st.button("Re-Rank All Ideas with AI"):
            try:
                # Get all ideas that need ranking
                ideas_to_rank = supabase.table("poppy_ideas_v2").select("*").execute().data
                
                # Process each idea
                for idea in ideas_to_rank:
                    # Get AI ranking score
                    score = get_ai_ranking_score(idea)
                    
                    # Update the idea's rank
                    supabase.table("poppy_ideas_v2").update({"rank": score}).eq("id", idea["id"]).execute()
                
                st.success("All ideas have been re-ranked using AI!")
                st.rerun()
            except Exception as e:
                st.error(f"Error re-ranking ideas: {str(e)}")
        
        # Make the DataFrame editable
        edited_df = st.data_editor(
            df,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select ideas to manage",
                    default=False,
                ),
                "Rank": st.column_config.NumberColumn(
                    "Rank",
                    help="Drag to reorder ideas",
                    min_value=0,
                    step=1,
                    default=0,
                ),
            },
            use_container_width=True
        )
        
        # Get selected ideas
        selected_ideas = edited_df[edited_df['Select'] == True]
        
        # Handle rank changes
        if not edited_df.equals(df):
            try:
                # Update ranks in database
                for _, row in edited_df.iterrows():
                    idea = next(
                        (i for i in all_ideas if i['title'] == row['Title']),
                        None
                    )
                    if idea and idea['rank'] != row['Rank']:
                        supabase.table("poppy_ideas_v2").update({"rank": row['Rank']}).eq("id", idea['id']).execute()
                st.success("Idea ranks have been updated!")
            except Exception as e:
                st.error(f"Error updating ranks: {str(e)}")
        
        # Create a clean management section
        with st.container():
            st.markdown("---")
            st.subheader("Manage Ideas")
            
            # Use columns for better layout
            col1, col2 = st.columns([1, 1])
            
            # Add some padding
            with col1:
                st.markdown("""
                <style>
                .stButton > button {
                    background-color: #dc3545;
                    color: white;
                    width: 100%;
                    padding: 10px;
                    border-radius: 8px;
                    font-weight: bold;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if st.button("Delete Selected Ideas"):
                    if len(selected_ideas) == 0:
                        st.warning("Please select at least one idea to delete!")
                    else:
                        try:
                            # Get the actual ideas from the database using their titles
                            for _, row in selected_ideas.iterrows():
                                idea = next(
                                    (i for i in all_ideas if i['title'] == row['Title']),
                                    None
                                )
                                if idea:
                                    # Delete idea_tags first (due to foreign key constraint)
                                    supabase.table("idea_tags").delete().eq("idea_id", idea['id']).execute()
                                    # Then delete the idea
                                    supabase.table("poppy_ideas_v2").delete().eq("id", idea['id']).execute()
                            st.success("Selected ideas have been deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting ideas: {str(e)}")
            
            with col2:
                st.markdown("""
                <style>
                .stButton > button {
                    background-color: #28a745;
                    color: white;
                    width: 100%;
                    padding: 10px;
                    border-radius: 8px;
                    font-weight: bold;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if st.button("Promote Selected Ideas"):
                    if len(selected_ideas) == 0:
                        st.warning("Please select at least one idea to promote!")
                    else:
                        try:
                            # Update the status of selected ideas to "In Progress"
                            for _, row in selected_ideas.iterrows():
                                idea = next(
                                    (i for i in all_ideas if i['title'] == row['Title']),
                                    None
                                )
                                if idea:
                                    # Get the status ID for "In Progress"
                                    status_id = next(
                                        s['id'] for s in status_options if s['name'] == 'In Progress'
                                    )
                                    # Update the idea's status
                                    supabase.table("poppy_ideas_v2").update({"status_id": status_id}).eq("id", idea['id']).execute()
                            st.success("Selected ideas have been promoted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error promoting ideas: {str(e)}")
    else:
        st.info("No ideas saved yet.")

# --- Display Ideas
def display_ideas():
    with st.expander("Filters", expanded=True):
        st.write("Current filters:")
        st.write(f"Status: {selected_status}")
        st.write(f"Priority: {selected_priority}")
        st.write(f"Category: {selected_category}")
    
    # Query ideas with filters
    query = supabase.table("poppy_ideas_v2")
    query = query.select("*")
    query = query.order("created_at", desc=True)
    
    if selected_priority_id:
        query = query.eq("priority_id", selected_priority_id)
    if selected_category_id:
        query = query.eq("category_id", selected_category_id)
    
    ideas = query.execute().data
    
    if ideas:
        for idea in ideas:
            with st.expander(f"{idea['title']} - {idea['created_at']}"):
                # Display basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Status:** {status_lookup.get(idea['status_id'], 'Unknown')}")
                with col2:
                    st.write(f"**Priority:** {priority_lookup.get(idea['priority_id'], 'Unknown')}")
                with col3:
                    st.write(f"**Category:** {category_lookup.get(idea['category_id'], 'Unknown')}")
                
                # Display description
                st.write("**Description:**")
                st.write(idea["description"] if idea["description"] else "No description")
                
                # Display source and context
                if idea["source"]:
                    st.write("**Source:**", idea["source"])
                if idea["context"]:
                    st.write("**Context:**", idea["context"])
                
                # Display tags
                if idea["id"]:
                    tags = supabase.table("idea_tags").select("tags.name").join("tags", "idea_tags.tag_id", "tags.id").eq("idea_id", idea["id"]).execute().data
                    if tags:
                        st.write("**Tags:**", ", ".join([t["name"] for t in tags]))
                
                # Display comments
                if idea["id"]:
                    comments = supabase.table("comments").select("*").eq("idea_id", idea["id"]).execute().data
                    if comments:
                        st.write("**Comments:**")
                        for comment in comments:
                            st.write(f"- {comment['content']} ({comment['created_at']})")
                
                # Add comment form
                with st.form(f"comment_{idea['id']}"):
                    comment_content = st.text_input("Add a comment", placeholder="Write your comment here...")
                    if st.form_submit_button("Add Comment"):
                        if comment_content:
                            supabase.table("comments").insert({
                                "idea_id": idea["id"],
                                "content": comment_content,
                                "creator_id": st.session_state.user_id if "user_id" in st.session_state else None
                            }).execute()
                            st.rerun()

# --- Footer
st.markdown("---")
st.caption("Poppy Dev v0.3 | Let's build something real.")
