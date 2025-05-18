import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import uuid
import pandas as pd

# --- Page config
st.set_page_config(page_title="Poppy Ideation", layout="wide")

# --- Initialize Supabase client
try:
    # Check if secrets exist
    st.write("Checking secrets...")
    st.write(f"Secrets object: {st.secrets}")
    st.write(f"Available secrets: {list(st.secrets.keys())}")
    
    # Try to get secrets
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "NOT_FOUND")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "NOT_FOUND")
    
    st.write(f"\nLoaded secrets:")
    st.write(f"URL: {SUPABASE_URL}")
    st.write(f"Key: {SUPABASE_KEY}")
    
    if SUPABASE_URL == "NOT_FOUND" or SUPABASE_KEY == "NOT_FOUND":
        st.error("Could not find Supabase credentials in secrets")
        st.stop()
        
    st.write(f"\nUsing URL: {SUPABASE_URL}")
    st.write(f"Key loaded: {'yes' if SUPABASE_KEY else 'no'}")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Error loading secrets: {str(e)}")
    st.stop()

# --- Header
st.title("Poppy Ideation")
st.success("Streamlit is up and running!")

# --- Helper function to get name lookups
def get_lookup(table_name):
    return {
        item['id']: item['name']
        for item in supabase.table(table_name).select("id, name").execute().data
    }

category_lookup = get_lookup("categories")
priority_lookup = get_lookup("priorities")
status_lookup = get_lookup("statuses")

# --- Sidebar
with st.sidebar:
    st.header("Filters")
    
    # Status filter
    status_options = supabase.table("statuses").select("id", "name").execute().data
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
st.write("---")

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
                    # Insert idea
                    idea_response = supabase.table("poppy_ideas_v2").insert(new_idea).execute()
                    idea_id = idea_response.data[0]["id"]
                    
                    # Link tags
                    for tag_name in tags:
                        tag = supabase.table("tags").select("id").eq("name", tag_name).execute().data[0]
                        supabase.table("idea_tags").insert({"idea_id": idea_id, "tag_id": tag["id"]}).execute()
                    
                    st.success("Idea created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating idea: {str(e)}")

    st.markdown("---")

    # Saved Ideas
    st.header("📁 Saved Ideas")
    ideas_response = supabase.table("poppy_ideas_v2").select("*").execute()
    ideas = ideas_response.data

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

    # Display saved ideas as a table
    if formatted_ideas:
        df = pd.DataFrame(formatted_ideas)
        st.dataframe(df, use_container_width=True)
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
