import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import uuid
import pandas as pd

# --- Page config
st.set_page_config(page_title="Poppy Ideation", layout="wide")

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

# --- Helper functions
def get_sprint_status(sprint):
    """Get sprint status based on dates"""
    today = datetime.now().date()
    start_date = datetime.fromisoformat(sprint['start_date']).date()
    end_date = datetime.fromisoformat(sprint['end_date']).date()
    
    if sprint['status'] == 'cancelled':
        return 'Cancelled'
    elif today < start_date:
        return 'Planned'
    elif start_date <= today <= end_date:
        return 'Active'
    else:
        return 'Completed'

def get_sprint_points(sprint_id):
    """Get total points for a sprint"""
    items = supabase.table("sprint_backlog")\
        .select("backlog_item_id")\
        .eq("sprint_id", sprint_id)\
        .execute().data
    
    points = 0
    for item in items:
        backlog_item = supabase.table("backlog_items")\
            .select("points")\
            .eq("id", item['backlog_item_id'])\
            .execute().data[0]
        points += backlog_item['points']
    return points

def get_sprint_velocity(sprint_id):
    """Calculate sprint velocity"""
    completed_items = supabase.table("sprint_backlog")\
        .select("backlog_item_id")\
        .eq("sprint_id", sprint_id)\
        .eq("status", "done")\
        .execute().data
    
    velocity = 0
    for item in completed_items:
        backlog_item = supabase.table("backlog_items")\
            .select("points")\
            .eq("id", item['backlog_item_id'])\
            .execute().data[0]
        velocity += backlog_item['points']
    return velocity

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

# --- Header
st.title("Poppy Ideation")
st.success("Streamlit is up and running!")

# --- Sidebar
with st.sidebar:
    st.header("Sprint Management")
    
    # Current sprint
    current_sprint = None
    sprints = supabase.table("sprints")\
        .select("id", "name", "start_date", "end_date", "status")\
        .execute().data
    
    if sprints:
        sprint_options = [f"{s['name']} ({s['start_date']} - {s['end_date']})" for s in sprints]
        selected_sprint = st.selectbox(
            "Select Sprint",
            sprint_options + ["Create New Sprint"],
            index=len(sprint_options)  # Default to "Create New Sprint"
        )
        
        if selected_sprint == "Create New Sprint":
            with st.form("new_sprint", clear_on_submit=True):
                sprint_name = st.text_input("Sprint Name")
                start_date = st.date_input("Start Date")
                end_date = st.date_input("End Date")
                
                if st.form_submit_button("Create Sprint"):
                    if sprint_name and start_date and end_date:
                        supabase.table("sprints").insert({
                            "name": sprint_name,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                            "status": "planned"
                        }).execute()
                        st.rerun()
        else:
            current_sprint = next(s for s in sprints 
                                if f"{s['name']} ({s['start_date']} - {s['end_date']})" == selected_sprint)
            
            # Sprint metrics
            st.subheader("Sprint Metrics")
            st.write(f"Status: {get_sprint_status(current_sprint)}")
            st.write(f"Planned Points: {get_sprint_points(current_sprint['id'])}")
            st.write(f"Velocity: {get_sprint_velocity(current_sprint['id'])}")

    # Backlog filters
    st.header("Backlog Filters")
    
    # Status filter
    status_options = [
        "backlog", "ready", "in_progress", "done", "blocked"
    ]
    selected_status = st.selectbox(
        "Status",
        status_options + ["All"],
        index=len(status_options)  # Default to "All"
    )
    
    # Priority filter
    priority_options = [
        "low", "medium", "high", "urgent"
    ]
    selected_priority = st.selectbox(
        "Priority",
        priority_options + ["All"],
        index=len(priority_options)  # Default to "All"
    )
    
    # Category filter
    category_options = supabase.table("categories").select("id", "name").execute().data
    selected_category = st.selectbox(
        "Category",
        [c["name"] for c in category_options] + ["All"],
        index=len(category_options)  # Default to "All"
    )

# --- Main Layout
# Create new backlog item section
with st.container():
    with st.form("new_backlog_item", clear_on_submit=True):
        st.header("➕ Create New Backlog Item")
        
        title = st.text_input("Title", placeholder="Enter a title for your item")
        description = st.text_area("Description", placeholder="Describe the user story or task")
        
        # Points estimation
        points = st.number_input("Story Points", min_value=1, max_value=100, value=5)
        
        # Status
        status = st.selectbox("Status", 
                             ["backlog", "ready", "in_progress", "done", "blocked"],
                             index=0)
        
        # Priority
        priority = st.selectbox("Priority", 
                              ["low", "medium", "high", "urgent"],
                              index=2)
        
        # Category
        category = st.selectbox("Category", 
                              [c["name"] for c in category_options],
                              index=0)
        
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
        
        submitted = st.form_submit_button("Add to Backlog")
        
        if submitted:
            if not title:
                st.warning("Please enter a title!")
            else:
                # Create the backlog item
                new_item = {
                    "title": title,
                    "description": description,
                    "category_id": next(c["id"] for c in category_options if c["name"] == category),
                    "status": status,
                    "priority": priority,
                    "points": points,
                    "creator_id": st.session_state.user_id if "user_id" in st.session_state else None
                }
                
                try:
                    item_response = supabase.table("backlog_items").insert(new_item).execute()
                    item_id = item_response.data[0]["id"]
                    
                    # Link tags
                    for tag_name in tags:
                        tag = supabase.table("tags").select("id").eq("name", tag_name).execute().data[0]
                        supabase.table("idea_tags").insert({"idea_id": item_id, "tag_id": tag["id"]}).execute()
                    
                    st.success("Backlog item created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating backlog item: {str(e)}")

    # Add a separator
    st.markdown("---")

# Ideas section
with st.container():
    st.header("💡 Ideas")
    
    # Apply filters from sidebar
    query = supabase.table("poppy_ideas_v2").select("*")
    
    # Apply filters
    if selected_status_id:
        query = query.eq("status_id", selected_status_id)
    if selected_priority_id:
        query = query.eq("priority_id", selected_priority_id)
    if selected_category_id:
        query = query.eq("category_id", selected_category_id)
    
    # Order by rank descending
    query = query.order("rank", desc=True)
    
    try:
        ideas_response = query.execute()
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
            
            # Add a column for selection
            formatted_ideas['Select'] = False
            
            # Configure the data editor
            edited_df = st.data_editor(
                formatted_ideas,
                hide_index=True,
                use_container_width=True,
                column_config={
                    'Select': st.column_config.CheckboxColumn(
                        "Select",
                        help="Select ideas to manage",
                        default=False
                    ),
                    'Rank': st.column_config.NumberColumn(
                        "Rank",
                        help="Drag to reorder ideas",
                        min_value=0,
                        max_value=100,
                        step=1,
                        format="%d"
                    ),
                    'Title': st.column_config.TextColumn(
                        "Title",
                        help="The title of the idea"
                    )
                }
            )
            
            # Handle changes to the DataFrame
            if not edited_df.equals(formatted_ideas):
                try:
                    # Update the database with any changes
                    for index, row in edited_df.iterrows():
                        if row['Rank'] != formatted_ideas.loc[index, 'Rank']:
                            supabase.table("poppy_ideas_v2").update({"rank": row['Rank']}).eq("id", ideas[index]['id']).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating rankings: {str(e)}")
            
            # Add management buttons
            with st.container():
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("Delete Selected Ideas", key="delete_button"):
                        try:
                            # Get selected ideas
                            selected_ideas = edited_df[edited_df['Select']].index
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
                            selected_ideas = edited_df[edited_df['Select']].index
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
    except Exception as e:
        st.error(f"Error fetching ideas: {str(e)}")

with st.container():
    st.header("Backlog and Sprint Items")
    
    try:
        # Get all backlog items
        backlog_items = supabase.table("backlog_items")\
            .select("*", "categories!inner(name)")\
            .execute().data
        
        # Get sprint backlog items if we have a current sprint
        sprint_items = []
        if current_sprint:
            sprint_items = supabase.table("sprint_backlog")\
                .select("*", "backlog_items!inner(*)", "backlog_items.categories!inner(name)")\
                .eq("sprint_id", current_sprint['id'])\
                .order("rank", ascending=True)\
                .execute().data
        
        if backlog_items or sprint_items:
            # Create DataFrames
            backlog_df = pd.DataFrame(backlog_items)
            sprint_df = pd.DataFrame(sprint_items)
            
            # Format DataFrames
            for df in [backlog_df, sprint_df]:
                if not df.empty:
                    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    df['category_name'] = df['category_id'].apply(lambda x: category_lookup.get(x, 'Unknown'))
                    
            # Display Backlog
            st.subheader("Product Backlog")
            if not backlog_df.empty:
                backlog_columns = [
                    'title', 'description', 'category_name', 'status', 'priority', 
                    'points', 'created_at'
                ]
                
                st.data_editor(
                    backlog_df[backlog_columns],
                    hide_index=True,
                    column_config={
                        'status': st.column_config.SelectboxColumn(
                            "Status",
                            options=["backlog", "ready", "in_progress", "done", "blocked"],
                            required=True
                        ),
                        'priority': st.column_config.SelectboxColumn(
                            "Priority",
                            options=["low", "medium", "high", "urgent"],
                            required=True
                        ),
                        'points': st.column_config.NumberColumn(
                            "Points",
                            min_value=1,
                            max_value=100,
                            required=True
                        )
                    },
                    use_container_width=True,
                    height=400)
            else:
                st.info("No backlog items found!")
            
            # Display Sprint Backlog if we have a current sprint
            if not sprint_df.empty:
                st.subheader(f"Sprint Backlog ({current_sprint['name']})")
                sprint_columns = [
                    'title', 'description', 'category_name', 'status', 'priority', 
                    'points', 'created_at', 'rank'
                ]
                
                st.data_editor(
                    sprint_df[sprint_columns],
                    hide_index=True,
                    column_config={
                        'status': st.column_config.SelectboxColumn(
                            "Status",
                            options=["backlog", "ready", "in_progress", "done", "blocked"],
                            required=True
                        ),
                        'priority': st.column_config.SelectboxColumn(
                            "Priority",
                            options=["low", "medium", "high", "urgent"],
                            required=True
                        ),
                        'points': st.column_config.NumberColumn(
                            "Points",
                            min_value=1,
                            max_value=100,
                            required=True
                        ),
                        'rank': st.column_config.NumberColumn(
                            "Rank",
                            help="Drag to reorder items within the sprint",
                            min_value=1,
                            required=True
                        )
                    },
                    use_container_width=True,
                    height=400
                )
            
        else:
            st.info("No backlog or sprint items found!")
            
    except Exception as e:
        st.error(f"Error fetching backlog items: {str(e)}")

        all_ideas = supabase.table("poppy_ideas_v2").select("id", "title", "rank").execute().data
        
        # Create a DataFrame with an additional column for selection
{{ ... }}
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

        # Footer
        st.markdown("---")
        st.caption("Poppy Dev v0.01 | Let's build something real.")

# Call display_ideas() at the top level
if __name__ == "__main__":
    display_ideas()
