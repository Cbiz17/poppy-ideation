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
    st.header("Sprint Management")
    sprints_response = supabase.table("sprints")\
        .select("id", "name", "start_date", "end_date", "status")\
        .execute()
    sprints = sprints_response.data if sprints_response.data else []
    
    if sprints:
        sprint_options_display = [f"{s['name']} ({s['start_date']} - {s['end_date']})" for s in sprints]
        selected_sprint_name = st.selectbox(
            "Select Sprint",
            sprint_options_display + ["Create New Sprint"],
            index=len(sprint_options_display) 
        )
        
        if selected_sprint_name == "Create New Sprint":
            with st.form("form_key", clear_on_submit=True):
                sprint_name_input = st.text_input("Sprint Name") # Renamed to avoid conflict
                start_date_input = st.date_input("Start Date") # Renamed
                end_date_input = st.date_input("End Date") # Renamed
                
                submitted = st.form_submit_button("Create Sprint")
                
                if submitted:
                    if sprint_name_input and start_date_input and end_date_input:
                        supabase.table("sprints").insert({
                            "name": sprint_name_input,
                            "start_date": start_date_input.isoformat(),
                            "end_date": end_date_input.isoformat(),
                            "status": "planned"
                        }).execute()
                        st.rerun()
        else:
            current_sprint = next((s for s in sprints 
                                if f"{s['name']} ({s['start_date']} - {s['end_date']})" == selected_sprint_name), None)
    else:
        st.info("No sprints found. You can create one.")
        
        # --- Test Form: Only text_input and submit button ---
        with st.form("text_input_only_test_form", clear_on_submit=True):
            # st.subheader("Create First Sprint") # Subheader removed for this test
            sprint_name_input = st.text_input("Sprint Name", key="init_sprint_form_name_v2") # Using the same key as before
            
            submitted_test_sprint = st.form_submit_button("Test Submit Name", key="test_sprint_name_submit")
            
            if submitted_test_sprint:
                st.success(f"Test form submitted with name: {sprint_name_input}")
        # --- End Test Form ---

    if current_sprint: 
        st.subheader("Sprint Metrics")
        st.write(f"Status: {get_sprint_status(current_sprint)}")
        st.write(f"Planned Points: {get_sprint_points(current_sprint['id'])}")
        st.write(f"Velocity: {get_sprint_velocity(current_sprint['id'])}")

    st.header("Filters")
    selected_status = st.selectbox("Status", status_options_list + ["All"], index=len(status_options_list))
    selected_priority = st.selectbox("Priority", priority_options_list + ["All"], index=len(priority_options_list))
    
    categories_response = supabase.table("categories").select("id", "name").execute()
    category_options_data = categories_response.data if categories_response.data else []
    category_names = [c["name"] for c in category_options_data]
    selected_category = st.selectbox("Category", category_names + ["All"], index=len(category_names))

    # Populate lookups and selected_ids based on selections
    status_response = supabase.table("statuses").select("id, name").execute()
    status_data = status_response.data if status_response.data else []
    status_lookup = {s['id']: s['name'] for s in status_data}
    selected_status_id = next((s['id'] for s in status_data if s['name'] == selected_status), None) if selected_status != "All" else None

    priority_response = supabase.table("priorities").select("id, name").execute()
    priority_data = priority_response.data if priority_response.data else []
    priority_lookup = {p['id']: p['name'] for p in priority_data}
    selected_priority_id = next((p['id'] for p in priority_data if p['name'] == selected_priority), None) if selected_priority != "All" else None
    
    category_lookup = {c['id']: c['name'] for c in category_options_data}
    selected_category_id = next((c['id'] for c in category_options_data if c['name'] == selected_category), None) if selected_category != "All" else None

st.title("Poppy Ideation")

# --- Main Layout Sections ---

def display_main_content():
    # Create new backlog item section
    with st.expander("➕ Create New Backlog Item", expanded=False):
        with st.form("new_backlog_item", clear_on_submit=True):
            title = st.text_input("Title", placeholder="Enter a title for your item")
            description = st.text_area("Description", placeholder="Describe the user story or task")
            points = st.number_input("Story Points", min_value=1, max_value=100, value=5)
            
            status_choice = st.selectbox("Status", status_options_list, index=0, key="nbi_status")
            priority_choice = st.selectbox("Priority", priority_options_list, index=2, key="nbi_priority")
            category_choice = st.selectbox("Category", category_names, index=0 if category_names else -1, key="nbi_category")
            
            tags_response = supabase.table("tags").select("id", "name").execute()
            tags_data = tags_response.data if tags_response.data else []
            tags_multiselect = st.multiselect("Tags", [t["name"] for t in tags_data], key="nbi_tags")
            
            submitted = st.form_submit_button("Add to Backlog")
            
            if submitted:
                if not title:
                    st.warning("Please enter a title!")
                else:
                    category_id_for_item = next((c["id"] for c in category_options_data if c["name"] == category_choice), None)
                    new_item_data = {
                        "title": title,
                        "description": description,
                        "category_id": category_id_for_item,
                        "status": status_choice, 
                        "priority": priority_choice, 
                        "points": points,
                        # "creator_id": st.session_state.user_id if "user_id" in st.session_state else None # Assuming user auth later
                    }
                    try:
                        insert_response = supabase.table("backlog_items").insert(new_item_data).execute()
                        if insert_response.data and len(insert_response.data) > 0:
                            item_id = insert_response.data[0]["id"]
                            for tag_name in tags_multiselect:
                                tag_id = next((t["id"] for t in tags_data if t["name"] == tag_name), None)
                                if tag_id:
                                    supabase.table("backlog_item_tags").insert({"backlog_item_id": item_id, "tag_id": tag_id}).execute()
                            st.success("Backlog item created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to create backlog item. Response: {insert_response}") # Log actual response
                    except Exception as e:
                        st.error(f"Error creating backlog item: {str(e)}")
    st.markdown("---")

    # Ideas section (Main display for poppy_ideas_v2)
    st.header("💡 Ideas")
    query_ideas = supabase.table("poppy_ideas_v2").select("*, statuses(name), priorities(name), categories(name)") # Fetch names directly
    if selected_status_id:
        query_ideas = query_ideas.eq("status_id", selected_status_id)
    if selected_priority_id:
        query_ideas = query_ideas.eq("priority_id", selected_priority_id)
    if selected_category_id:
        query_ideas = query_ideas.eq("category_id", selected_category_id)
    query_ideas = query_ideas.order("rank", desc=True)
    
    try:
        ideas_response_main = query_ideas.execute()
        ideas_main = ideas_response_main.data if ideas_response_main.data else []
        
        if ideas_main:
            df_ideas_main = pd.DataFrame(ideas_main)
            formatted_ideas_main = df_ideas_main[['id','title', 'description', 'rank', 'statuses', 'priorities', 'categories', 'created_at']].copy()
            formatted_ideas_main.rename(columns={
                'id': 'ID', 'title': 'Title', 'description': 'Description', 'rank': 'Rank',
                'statuses': 'Status', 'priorities': 'Priority', 'categories': 'Category', 'created_at': 'Created At'
            }, inplace=True)

            # Extract names from nested dicts
            formatted_ideas_main['Status'] = formatted_ideas_main['Status'].apply(lambda x: x['name'] if x else 'N/A')
            formatted_ideas_main['Priority'] = formatted_ideas_main['Priority'].apply(lambda x: x['name'] if x else 'N/A')
            formatted_ideas_main['Category'] = formatted_ideas_main['Category'].apply(lambda x: x['name'] if x else 'N/A')
            
            formatted_ideas_main['Select'] = False
            
            edited_df_ideas = st.data_editor(
                formatted_ideas_main,
                hide_index=True,
                use_container_width=True,
                column_config={
                    'ID': None, 
                    'Select': st.column_config.CheckboxColumn("Select", help="Select ideas to manage", default=False),
                    'Rank': st.column_config.NumberColumn("Rank", help="Drag to reorder ideas", min_value=0, max_value=1000, step=1, format="%d"),
                    'Title': st.column_config.TextColumn("Title", help="The title of the idea"),
                    'Description': None, 'Created At': None # Hide some cols for brevity in editor
                },
                key="ideas_data_editor"
            )
            
            if st.button("Save Idea Changes", key="save_idea_changes"):
                try:
                    for index, row in edited_df_ideas.iterrows():
                        original_idea_id = formatted_ideas_main.loc[index, 'ID']
                        # Compare editable fields like Rank or others if you add them
                        if row['Rank'] != formatted_ideas_main.loc[index, 'Rank']:
                            supabase.table("poppy_ideas_v2").update({"rank": row['Rank']}).eq("id", original_idea_id).execute()
                    st.success("Idea changes saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating ideas: {str(e)}")
            
            selected_rows_df = edited_df_ideas[edited_df_ideas['Select']]
            if not selected_rows_df.empty:
                st.subheader("Selected Idea Actions")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete Selected Ideas", key="delete_ideas_button"):
                        for idea_id_to_delete in selected_rows_df['ID']:
                            supabase.table("backlog_item_tags").delete().eq("backlog_item_id", idea_id_to_delete).execute()
                            supabase.table("poppy_ideas_v2").delete().eq("id", idea_id_to_delete).execute()
                        st.success("Selected ideas deleted successfully!")
                        st.rerun()
                with col2:
                    if st.button("Promote Selected Ideas", key="promote_ideas_button"):
                        in_progress_status_id = next((sid for sid, sname in status_lookup.items() if sname == "In Progress"), None)
                        if in_progress_status_id:
                            for idea_id_to_promote in selected_rows_df['ID']:
                                supabase.table("poppy_ideas_v2").update({"status_id": in_progress_status_id}).eq("id", idea_id_to_promote).execute()
                            st.success("Selected ideas promoted to In Progress!")
                            st.rerun()
                        else:
                            st.error("Could not find 'In Progress' status ID.")
            # AI Re-ranking button - get_ai_ranking_score needs to be defined
            # def get_ai_ranking_score(idea): pass # Placeholder
            if st.button("Re-Rank All Ideas with AI (Not Implemented)", key="re_rank_ideas_button"):
                st.info("AI Re-ranking feature placeholder.")
        else:
            st.info("No ideas found based on current filters!")
    except Exception as e:
        st.error(f"Error fetching ideas: {str(e)}")
    st.markdown("---")

    # Backlog and Sprint Items Display Section
    st.header("Backlog and Sprint Items")
    try:
        backlog_items_response = supabase.table("backlog_items")\
            .select("*, categories(name)")\
            .execute()
        backlog_items = backlog_items_response.data if backlog_items_response.data else []
        
        sprint_items_display = []
        if current_sprint:
            sprint_items_response = supabase.table("sprint_backlog")\
                .select("*, backlog_items(*, categories(name))")\
                .eq("sprint_id", current_sprint['id'])\
                .order("rank", ascending=True)\
                .execute()
            sprint_items_display = sprint_items_response.data if sprint_items_response.data else []
        
        st.subheader("Product Backlog")
        if backlog_items:
            backlog_df_display = pd.DataFrame(backlog_items)
            if not backlog_df_display.empty:
                backlog_df_display['category_name'] = backlog_df_display['categories'].apply(lambda x: x['name'] if x and isinstance(x, dict) else 'N/A')
                backlog_df_display['created_at'] = pd.to_datetime(backlog_df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                backlog_cols_to_show = ['title', 'description', 'category_name', 'status', 'priority', 'points', 'created_at']
                backlog_cols_to_show = [col for col in backlog_cols_to_show if col in backlog_df_display.columns]

                edited_backlog_df = st.data_editor(
                    backlog_df_display[backlog_cols_to_show],
                    hide_index=True,
                    column_config={
                        'status': st.column_config.SelectboxColumn("Status", options=status_options_list, required=True),
                        'priority': st.column_config.SelectboxColumn("Priority", options=priority_options_list, required=True),
                        'points': st.column_config.NumberColumn("Points", min_value=1, max_value=100, required=True)
                    },
                    use_container_width=True, height=300, key="product_backlog_editor"
                )
                # Add save functionality for edited_backlog_df if needed
            else:
                st.info("No backlog items found!")
        else:
            st.info("No backlog items found!")
        
        if current_sprint and sprint_items_display:
            st.subheader(f"Sprint Backlog ({current_sprint['name']})")
            processed_sprint_items = []
            for item in sprint_items_display:
                bi = item.get('backlog_items', {})
                cat = bi.get('categories', {})
                processed_item = {
                    'title': bi.get('title', 'N/A'), 'description': bi.get('description', 'N/A'),
                    'category_name': cat.get('name', 'N/A') if isinstance(cat, dict) else 'N/A',
                    'status': item.get('status', bi.get('status', 'N/A')), 
                    'priority': bi.get('priority', 'N/A'), 'points': bi.get('points', 0),
                    'created_at': pd.to_datetime(bi.get('created_at')).strftime('%Y-%m-%d %H:%M') if bi.get('created_at') else 'N/A',
                    'rank': item.get('rank', 0)
                }
                processed_sprint_items.append(processed_item)
            
            sprint_df_display = pd.DataFrame(processed_sprint_items)
            if not sprint_df_display.empty:
                sprint_cols_to_show = ['title', 'description', 'category_name', 'status', 'priority', 'points', 'created_at', 'rank']
                sprint_cols_to_show = [col for col in sprint_cols_to_show if col in sprint_df_display.columns]
                edited_sprint_df = st.data_editor(
                    sprint_df_display[sprint_cols_to_show],
                    hide_index=True,
                    column_config={
                        'status': st.column_config.SelectboxColumn("Status", options=status_options_list, required=True),
                        'priority': st.column_config.SelectboxColumn("Priority", options=priority_options_list, required=True),
                        'points': st.column_config.NumberColumn("Points", min_value=1, max_value=100, required=True),
                        'rank': st.column_config.NumberColumn("Rank", help="Drag to reorder items", min_value=1, required=True)
                    },
                    use_container_width=True, height=300, key="sprint_backlog_editor"
                )
                # Add save functionality for edited_sprint_df if needed
            else:
                st.info(f"No items found in sprint: {current_sprint['name']}")
        elif current_sprint:
             st.info(f"No items found in sprint: {current_sprint['name']}")
        else: # No current sprint selected, so don't show sprint backlog
            pass 
            
    except Exception as e:
        st.error(f"Error displaying backlog/sprint items: {str(e)}")

# --- Entry point ---
if __name__ == "__main__":
    display_main_content() # Call the main function that lays out the UI
