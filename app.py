import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv

# --- Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Page config
st.set_page_config(page_title="Poppy Ideation", layout="centered")

# --- Header
st.title("🧠 Poppy Ideation")

# --- Welcome
st.success("Streamlit is up and running!")

# --- Input
st.header("💡 Log a New Idea")
idea = st.text_input("Type in an idea you’d like to save:")

if st.button("Save Idea"):
    if idea.strip() == "":
        st.warning("You must enter something first!")
    else:
        # --- Save to Supabase
        response = supabase.table("poppy_ideas").insert({"content": idea}).execute()
        if response.data:
            st.success("Idea saved successfully!")
        else:
            st.error(f"Something went wrong: {response.error}")

# --- Display
st.header("🗂 Saved Ideas")

# --- Retrieve from Supabase
ideas_response = supabase.table("poppy_ideas").select("*").order("created_at", desc=True).execute()

if ideas_response.data:
    for entry in ideas_response.data:
        st.markdown(f"**• {entry['content']}**  \n🕓 {entry['created_at']}")
else:
    st.write("No ideas logged yet.")

# --- Footer
st.markdown("---")
st.caption("Poppy Dev v0.2 | Let’s build something real.")