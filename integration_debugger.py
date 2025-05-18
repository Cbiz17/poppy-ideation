import streamlit as st
import threading
import time

# Global log storage (thread-safe)
_integration_log = []
_log_lock = threading.Lock()

# Monkey-patch for Supabase client
_supabase_patched = False

def patch_supabase_client(supabase_client):
    global _supabase_patched
    if _supabase_patched:
        return
    orig_from = supabase_client.from_
    def from_patch(table_name):
        orig_query = orig_from(table_name)
        # Only patch .execute if it exists
        if hasattr(orig_query, 'execute'):
            orig_execute = orig_query.execute
            def execute_patch(*args, **kwargs):
                query_info = f"Supabase Query: {table_name} | Args: {args} | Kwargs: {kwargs}"
                with _log_lock:
                    _integration_log.append((time.time(), 'QUERY', query_info))
                try:
                    result = orig_execute(*args, **kwargs)
                    with _log_lock:
                        _integration_log.append((time.time(), 'RESPONSE', str(result)))
                    return result
                except Exception as e:
                    with _log_lock:
                        _integration_log.append((time.time(), 'ERROR', str(e)))
                    raise
            orig_query.execute = execute_patch
        return orig_query
    supabase_client.from_ = from_patch
    _supabase_patched = True

def show_integration_log():
    st.markdown("---")
    st.subheader("🔍 Integration Debugger Log")
    if st.button("Refresh Log", key="refresh_integration_log"):
        st.rerun()
    with _log_lock:
        log_copy = list(_integration_log)
    if not log_copy:
        st.info("No integration events logged yet.")
    else:
        log_lines = []
        for ts, event_type, details in log_copy[-100:]:  # Show last 100 events
            tstr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            color = '#FFB4A2' if event_type == 'ERROR' else '#4F8A8B'
            log_lines.append(f"<div style='color:{color};font-size:0.95em;'><b>[{tstr}] {event_type}:</b> {details}</div>")
        st.markdown(
            f"<div style='max-height:300px;overflow-y:auto;background:#F5F7FA;border-radius:8px;padding:0.7em 1em 0.7em 1em;border:1px solid #E9ECEF;'>{''.join(log_lines)}</div>",
            unsafe_allow_html=True
        )
    st.markdown("---") 