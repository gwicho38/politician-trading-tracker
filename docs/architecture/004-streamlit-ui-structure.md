# ADR-004: Streamlit UI File Structure

## Status
Proposed

## Context

Currently, Streamlit page files live in `src/` alongside the core library:

```
src/
    politician_trading/     # Core library
    1_Data_Collection.py    # Streamlit pages
    2_Trading_Signals.py
    3_Trading_Operations.py
    ...
    auth_utils.py           # UI utilities
    models.py               # Duplicate of politician_trading/models
```

Issues:
1. **Mixed concerns**: UI code alongside library code
2. **Emoji filenames**: Non-standard Python naming
3. **Duplicate files**: `models.py` duplicated
4. **Import confusion**: Unclear what's library vs UI

## Decision (Proposed)

Move Streamlit UI to a dedicated directory:

```
src/
    politician_trading/     # Core library (unchanged)
app/
    __init__.py
    Home.py                 # Main entry point
    pages/
        1_Data_Collection.py
        2_Trading_Signals.py
        3_Trading_Operations.py
        ...
    components/
        auth.py             # Auth utilities (consolidated)
        charts.py           # Reusable chart components
        sidebar.py          # Sidebar components
    utils/
        formatting.py       # Display formatting helpers
```

Configuration in `.streamlit/config.toml`:
```toml
[server]
baseUrlPath = ""

[pages]
root = "app"
```

## Consequences

### Positive
- **Clear separation**: Library vs UI is obvious
- **Reusable library**: `politician_trading` can be used independently
- **Standard structure**: Follows Streamlit multipage conventions
- **Cleaner imports**: No more path manipulation

### Negative
- **Migration effort**: Update all page paths
- **Configuration changes**: Update Streamlit config
- **CI/CD updates**: Update deployment scripts

### Migration Plan
1. Create `app/` directory structure
2. Move page files, removing emoji prefixes (keep numbers)
3. Update imports to use absolute paths
4. Update `.streamlit/config.toml`
5. Update deployment configuration
6. Remove duplicate files from `src/`
