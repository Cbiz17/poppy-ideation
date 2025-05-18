import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import uuid
import pandas as pd

# --- Page config
st.set_page_config(page_title="Poppy Ideation", layout="wide")

# --- Custom CSS for modern, creative, collaborative look ---
st.markdown(
    """
    <style>
    html, body, [class*=\"css\"]  { font-family: 'Inter', 'Nunito', 'Segoe UI', 'sans-serif' !important; }
    .stApp { background-color: #F5F7FA; }
    .stButton>button, .stForm button, .stDownloadButton>button {
        background-color: #4F8A8B;
        color: #fff;
        border-radius: 8px;
        padding: 0.5em 1.2em;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(79,138,139,0.08);
        border: none;
        transition: background 0.2s;
    }
    .stButton>button:hover, .stForm button:hover, .stDownloadButton>button:hover {
        background-color: #FFB4A2;
        color: #22223B;
    }
    .stTabs [data-baseweb=\"tab\"] {
        font-weight: 600;
        color: #4F8A8B;
        border-radius: 8px 8px 0 0;
        background: #F5F7FA;
        margin-right: 2px;
    }
    .stTabs [aria-selected=\"true\"] {
        background: #E9ECEF;
        color: #22223B;
        border-bottom: 2px solid #FFB4A2;
    }
    .stDataFrame, .stDataEditor, .stTextInput, .stTextArea, .stSelectbox, .stNumberInput, .stExpander, .stForm {
        border-radius: 12px !important;
        box-shadow: 0 1px 8px rgba(34,34,59,0.06);
        background: #E9ECEF !important;
        padding: 1.2em !important;
        margin-bottom: 1.2em !important;
    }
    .stExpanderHeader {
        font-weight: 600;
        color: #4F8A8B;
    }
    .stAlert, .stInfo, .stSuccess, .stError {
        border-radius: 8px !important;
    }
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.2em 0.7em;
        border-radius: 999px;
        font-size: 0.9em;
        font-weight: 600;
        margin-right: 0.5em;
    }
    .status-idea { background: #E0F2FE; color: #4F8A8B; }
    .status-backlog { background: #FFF3CD; color: #FFB4A2; }
    .status-in_progress { background: #EDE7F6; color: #5A7D7C; }
    .status-done { background: #E6F4EA; color: #43AA8B; }
    .status-blocked { background: #FFF0F3; color: #FF006E; }
    </style>
    """,
    unsafe_allow_html=True
)

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

    selected_priority = st.selectbox("Priority", ["All"] + priorities)
    selected_category = st.selectbox("Category", ["All"] + category_names)

    # Sprints
    sprints_response = supabase.table("sprints").select("id", "name", "start_date", "end_date", "status", "goal").execute()
    sprints = sprints_response.data if sprints_response.data else []
    sprint_names = [s["name"] for s in sprints]

    # Use session_state for selected sprint
    if "selected_sprint" not in st.session_state:
        st.session_state.selected_sprint = "All"
    selected_sprint = st.selectbox("Sprint", ["All"] + sprint_names, index=(["All"] + sprint_names).index(st.session_state.selected_sprint) if st.session_state.selected_sprint in ["All"] + sprint_names else 0, key="sprint_select")
    st.session_state.selected_sprint = selected_sprint

    # Create New Sprint
    with st.expander("Create New Sprint"):
        with st.form("create_sprint_form", clear_on_submit=True):
            sprint_name = st.text_input("Sprint Name")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            goal = st.text_area("Goal (optional)")
            submitted = st.form_submit_button("Create Sprint")
            if submitted and sprint_name and start_date and end_date:
                try:
                    result = supabase.table("sprints").insert({
                        "name": sprint_name,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "status": "planned",
                        "goal": goal
                    }).execute()
                    st.success("Sprint created!")
                    # Auto-select the new sprint
                    st.session_state.selected_sprint = sprint_name
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error creating sprint: {str(e)}")

    # Manage Sprints Modal/Section
    if "show_manage_sprints" not in st.session_state:
        st.session_state.show_manage_sprints = False
    if st.button("Manage Sprints"):
        st.session_state.show_manage_sprints = True
    if st.session_state.show_manage_sprints:
        st.markdown("---")
        st.subheader(":wrench: Manage Sprints")
        sprint_df = pd.DataFrame(sprints)
        if not sprint_df.empty:
            sprint_df_display = sprint_df[["name", "start_date", "end_date", "status", "goal"]]
            st.dataframe(sprint_df_display, use_container_width=True)
            # Edit/Delete actions
            for idx, row in sprint_df.iterrows():
                with st.expander(f"Edit: {row['name']}"):
                    with st.form(f"edit_sprint_form_{row['id']}", clear_on_submit=True):
                        new_name = st.text_input("Sprint Name", value=row["name"])
                        new_start = st.date_input("Start Date", value=pd.to_datetime(row["start_date"]).date())
                        new_end = st.date_input("End Date", value=pd.to_datetime(row["end_date"]).date())
                        new_status = st.selectbox("Status", ["planned", "active", "completed", "cancelled"], index=["planned", "active", "completed", "cancelled"].index(row["status"]))
                        new_goal = st.text_area("Goal", value=row.get("goal", ""))
                        save = st.form_submit_button("Save Changes")
                        delete = st.form_submit_button("Delete Sprint")
                        if save:
                            try:
                                supabase.table("sprints").update({
                                    "name": new_name,
                                    "start_date": new_start.isoformat(),
                                    "end_date": new_end.isoformat(),
                                    "status": new_status,
                                    "goal": new_goal
                                }).eq("id", row["id"]).execute()
                                st.success("Sprint updated!")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Error updating sprint: {str(e)}")
                        if delete:
                            try:
                                supabase.table("sprints").delete().eq("id", row["id"]).execute()
                                st.success("Sprint deleted!")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Error deleting sprint: {str(e)}")
        else:
            st.info("No sprints found.")
        if st.button("Close Sprint Manager"):
            st.session_state.show_manage_sprints = False
            st.experimental_rerun()

# --- Sprint Details Card ---
def show_sprint_details(selected_sprint_name, sprints):
    if selected_sprint_name != "All":
        sprint = next((s for s in sprints if s["name"] == selected_sprint_name), None)
        if sprint:
            st.markdown("---")
            st.markdown(f"### :dart: Sprint Details: {sprint['name']}")
            st.write(f"**Dates:** {sprint['start_date']} to {sprint['end_date']}")
            st.write(f"**Status:** {sprint['status']}")
            if sprint.get("goal"):
                st.write(f"**Goal:** {sprint['goal']}")
            # Optionally, add metrics here (points, velocity, etc.)

st.title("Poppy Ideation")

# --- Main Layout Sections ---
def display_main_content():
    show_sprint_details(st.session_state.selected_sprint, sprints)
    # Tabs for each status
    statuses = ["idea", "backlog", "in_progress", "done", "blocked"]
    status_labels = ["Idea", "Backlog", "In Progress", "Done", "Blocked"]
    tab_objs = st.tabs(status_labels)

    for i, (tab, status) in enumerate(zip(tab_objs, statuses)):
        with tab:
            # Fetch items for this status
            query = supabase.table("items").select("*", "categories(name)", "sprints(name)")
            query = query.eq("status", status)
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

            # Add/Edit Item Form (only in the first tab for clarity)
            if i == 0:
                with st.form("add_edit_item_form", clear_on_submit=True):
                    title = st.text_input("Title")
                    description = st.text_area("Description")
                    form_status = st.selectbox("Status", statuses, index=0)
                    priority = st.selectbox("Priority", priorities)
                    category = st.selectbox("Category", category_names)
                    points = st.number_input("Points", min_value=0, max_value=100, value=0)
                    submitted = st.form_submit_button("Add Item")
                    if submitted and title:
                        category_id = next((c["id"] for c in category_options_data if c["name"] == category), None)
                        supabase.table("items").insert({
                            "title": title,
                            "description": description,
                            "status": form_status,
                            "priority": priority,
                            "category_id": category_id,
                            "points": points
                        }).execute()
                        st.success("Item added!")
                        # Switch to the tab matching the new item's status
                        st.experimental_set_query_params(tab=form_status)
                        st.rerun()

            st.markdown("---")
            # Items Table for this status
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
                        key=f"items_data_editor_{status}"
                    )
                    # Save changes
                    if st.button("Save Changes", key=f"save_item_changes_{status}"):
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
                            if st.button("Delete Selected Items", key=f"delete_items_button_{status}"):
                                for item_id in selected_rows_df["id"]:
                                    supabase.table("items").delete().eq("id", item_id).execute()
                                st.success("Selected items deleted!")
                                st.rerun()
                        with col2:
                            if st.button("Promote Selected Items", key=f"promote_items_button_{status}"):
                                for item_id in selected_rows_df["id"]:
                                    supabase.table("items").update({"status": "in_progress"}).eq("id", item_id).execute()
                                st.success("Selected items promoted to In Progress!")
                                st.rerun()
                    # AI Re-ranking button
                    if st.button("Re-Rank All Items with AI (Not Implemented)", key=f"re_rank_items_button_{status}"):
                        st.info("AI Re-ranking feature placeholder.")
            else:
                st.info("No items found based on current filters!")

# --- Entry point ---
if __name__ == "__main__":
    display_main_content() # Call the main function that lays out the UI
