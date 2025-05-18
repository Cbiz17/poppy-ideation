import threading
import time
import streamlit as st

# Global event log and lock
_mcp_log = []
_mcp_lock = threading.Lock()
_registered_clients = {}

# Known error patterns and fixes
KNOWN_ISSUES = [
    {
        'pattern': 'column reference "id" is ambiguous',
        'suggestion': 'Use fully qualified column names, e.g., idea_embeddings.id',
        'autofix': False  # Set to True if you want to try auto-patching
    },
    {
        'pattern': 'Could not find the',
        'suggestion': 'Check if the column exists in your schema and matches your code.',
        'autofix': False
    },
    # Add more patterns as needed
]

def log_event(event_type, details):
    with _mcp_lock:
        _mcp_log.append((time.time(), event_type, details))

def analyze_event(event):
    ts, typ, msg = event
    for issue in KNOWN_ISSUES:
        if issue['pattern'].lower() in msg.lower():
            return issue['suggestion']
    return None

def register_client(client, name):
    _registered_clients[name] = client
    # Example: Patch Supabase client
    if hasattr(client, 'from_'):
        orig_from = client.from_
        def from_patch(table_name):
            orig_query = orig_from(table_name)
            orig_execute = orig_query.execute
            def execute_patch(*args, **kwargs):
                log_event('QUERY', f"{name}: {table_name} | Args: {args} | Kwargs: {kwargs}")
                try:
                    result = orig_execute(*args, **kwargs)
                    log_event('RESPONSE', str(result))
                    return result
                except Exception as e:
                    log_event('ERROR', str(e))
                    return result
            orig_query.execute = execute_patch
            return orig_query
        client.from_ = from_patch

def show_mcp_dashboard():
    st.sidebar.markdown("---")
    st.sidebar.subheader(":robot_face: MCP Integration Dashboard")
    with _mcp_lock:
        for event in list(_mcp_log)[-30:]:
            ts, typ, msg = event
            suggestion = analyze_event(event)
            color = 'red' if typ == 'ERROR' else ('orange' if suggestion else 'black')
            st.sidebar.markdown(f"<div style='color:{color};font-size:0.85em'><b>{typ}:</b> {msg}</div>", unsafe_allow_html=True)
            if suggestion:
                st.sidebar.markdown(f"<div style='color:blue;font-size:0.8em'><b>Suggestion:</b> {suggestion}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---") 