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

# --- Global variable initializations for filters and lookups (will be populated in sidebar)
status_lookup = {} 
priority_lookup = {}
category_lookup = {}
selected_status_id = None
selected_priority_id = None
selected_category_id = None
selected_status = "All"
selected_priority = "All"
selected_category = "All"
status_options_list = ["backlog", "ready", "in_progress", "done", "blocked"]
priority_options_list = ["low", "medium", "high", "urgent"]
category_names = []
current_sprint = None # Initialize current_sprint globally

# --- Sidebar
with st.sidebar:
    st.header("Filters")
    # Fetch categories, priorities, statuses, sprints
    categories_response = supabase.table("categories").select("id", "name").execute()
    category_options_data = categories_response.data if categories_response.data else []
    category_names = [c["name"] for c in category_options_data]

    priorities = ["low", "medium", "high", "urgent"]
    statuses = ["idea", "backlog", "in_progress", "done", "blocked"]

    selected_status = st.selectbox("Status", ["All"] + statuses)
    selected_priority = st.selectbox("Priority", ["All"] + priorities)
    selected_category = st.selectbox("Category", ["All"] + category_names)

    # Sprints
    sprints_response = supabase.table("sprints").select("id", "name", "start_date", "end_date", "status").execute()
    sprints = sprints_response.data if sprints_response.data else []
    sprint_names = [s["name"] for s in sprints]
    selected_sprint = st.selectbox("Sprint", ["All"] + sprint_names)

    if st.button("Create New Sprint"):
        with st.form("create_sprint_form", clear_on_submit=True):
            sprint_name = st.text_input("Sprint Name")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            submitted = st.form_submit_button("Create Sprint")
            if submitted and sprint_name and start_date and end_date:
                supabase.table("sprints").insert({
                    "name": sprint_name,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "status": "planned"
                }).execute()
                st.success("Sprint created!")
                st.rerun()

st.title("Poppy Ideation")

# --- Main Layout Sections ---
def display_main_content():
    # Fetch items
    query = supabase.table("items").select("*", "categories(name)", "sprints(name)")
    if selected_status != "All":
        query = query.eq("status", selected_status)
    if selected_priority != "All":
        query = query.eq("priority", selected_priority)
    if selected_category != "All":
        cat_id = next((c["id"] for c in category_options_data if c["name"] == selected_category), None)
        if cat_id:
            query = query.eq("category_id", cat_id)
    if selected_sprint != "All":
        sprint_id = next((s["id"] for s in sprints if s["name"] == selected_sprint), None)
        if sprint_id:
            query = query.eq("sprint_id", sprint_id)
    query = query.order("rank", desc=True)
    items_response = query.execute()
    items = items_response.data if items_response.data else []

    # Add/Edit Item Form
    with st.form("add_edit_item_form", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description")
        status = st.selectbox("Status", statuses)
        priority = st.selectbox("Priority", priorities)
        category = st.selectbox("Category", category_names)
        points = st.number_input("Points", min_value=0, max_value=100, value=0)
        submitted = st.form_submit_button("Add Item")
        if submitted and title:
            category_id = next((c["id"] for c in category_options_data if c["name"] == category), None)
            supabase.table("items").insert({
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "category_id": category_id,
                "points": points
            }).execute()
            st.success("Item added!")
            st.rerun()

    st.markdown("---")
    # Unified Items Table
    if items:
        df = pd.DataFrame(items)
        if not df.empty:
            df["Select"] = False
            edited_df = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", help="Select items to manage", default=False),
                    "rank": st.column_config.NumberColumn("Rank", help="Drag to reorder items", min_value=0, max_value=1000, step=1, format="%d"),
                    "title": st.column_config.TextColumn("Title", help="The title of the item"),
                    "description": None, "created_at": None
                },
                key="items_data_editor"
            )
            # Save changes
            if st.button("Save Changes", key="save_item_changes"):
                try:
                    for index, row in edited_df.iterrows():
                        original_id = df.loc[index, "id"]
                        if row["rank"] != df.loc[index, "rank"]:
                            supabase.table("items").update({"rank": row["rank"]}).eq("id", original_id).execute()
                    st.success("Changes saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating items: {str(e)}")
            # Bulk actions
            selected_rows_df = edited_df[edited_df["Select"]]
            if not selected_rows_df.empty:
                st.subheader("Selected Item Actions")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete Selected Items", key="delete_items_button"):
                        for item_id in selected_rows_df["id"]:
                            supabase.table("items").delete().eq("id", item_id).execute()
                        st.success("Selected items deleted!")
                        st.rerun()
                with col2:
                    if st.button("Promote Selected Items", key="promote_items_button"):
                        for item_id in selected_rows_df["id"]:
                            supabase.table("items").update({"status": "in_progress"}).eq("id", item_id).execute()
                        st.success("Selected items promoted to In Progress!")
                        st.rerun()
            # AI Re-ranking button
            if st.button("Re-Rank All Items with AI (Not Implemented)", key="re_rank_items_button"):
                st.info("AI Re-ranking feature placeholder.")
    else:
        st.info("No items found based on current filters!")

# --- Entry point ---
if __name__ == "__main__":
    display_main_content() # Call the main function that lays out the UI
