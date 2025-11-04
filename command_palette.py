"""
Command Palette for Politician Trading Tracker
Provides CMD+K / CTRL+K searchable modal interface for all app features
"""
import streamlit as st
from typing import List, Dict, Callable, Optional


class CommandPalette:
    """Command palette with fuzzy search for app navigation and actions"""

    def __init__(self):
        self.commands: List[Dict] = []
        self._register_default_commands()

    def _register_default_commands(self):
        """Register default navigation and feature commands"""

        # Page navigation commands
        self.add_command(
            "Data Collection",
            lambda: st.switch_page("1_📥_Data_Collection.py"),
            category="Navigation",
            keywords=["data", "collection", "fetch", "scrape", "download"],
            icon="📥"
        )

        self.add_command(
            "Trading Signals",
            lambda: st.switch_page("2_🎯_Trading_Signals.py"),
            category="Navigation",
            keywords=["signals", "trading", "buy", "sell", "recommendations"],
            icon="🎯"
        )

        self.add_command(
            "Trading Operations",
            lambda: st.switch_page("3_💼_Trading_Operations.py"),
            category="Navigation",
            keywords=["operations", "trade", "execute", "orders"],
            icon="💼"
        )

        self.add_command(
            "Portfolio",
            lambda: st.switch_page("4_📈_Portfolio.py"),
            category="Navigation",
            keywords=["portfolio", "holdings", "positions", "performance"],
            icon="📈"
        )

        self.add_command(
            "Scheduled Jobs",
            lambda: st.switch_page("5_⏰_Scheduled_Jobs.py"),
            category="Navigation",
            keywords=["jobs", "scheduled", "automation", "cron", "tasks"],
            icon="⏰"
        )

        self.add_command(
            "Settings",
            lambda: st.switch_page("6_⚙️_Settings.py"),
            category="Navigation",
            keywords=["settings", "config", "configuration", "preferences"],
            icon="⚙️"
        )

        self.add_command(
            "Database Setup",
            lambda: st.switch_page("7_🔧_Database_Setup.py"),
            category="Navigation",
            keywords=["database", "setup", "schema", "tables", "migration"],
            icon="🔧"
        )

        self.add_command(
            "Action Logs",
            lambda: st.switch_page("8_📋_Action_Logs.py"),
            category="Navigation",
            keywords=["logs", "actions", "history", "audit", "events"],
            icon="📋"
        )

        self.add_command(
            "Auth Test",
            lambda: st.switch_page("99_🧪_Auth_Test.py"),
            category="Navigation",
            keywords=["auth", "authentication", "test", "login", "session"],
            icon="🧪"
        )

        # Feature commands
        self.add_command(
            "Refresh",
            lambda: st.rerun(),
            category="Actions",
            keywords=["refresh", "reload", "update", "rerun"],
            icon="🔄"
        )

        self.add_command(
            "Clear Cache",
            lambda: st.cache_data.clear(),
            category="Actions",
            keywords=["clear", "cache", "reset", "clean"],
            icon="🗑️"
        )

        self.add_command(
            "Shortcuts",
            self._show_shortcuts,
            category="Help",
            keywords=["shortcuts", "hotkeys", "keyboard", "help"],
            icon="⌨️"
        )

    def add_command(
        self,
        name: str,
        action: Callable,
        category: str = "General",
        keywords: Optional[List[str]] = None,
        icon: str = "•"
    ):
        """Add a command to the palette"""
        self.commands.append({
            "name": name,
            "action": action,
            "category": category,
            "keywords": keywords or [],
            "icon": icon
        })

    def _show_shortcuts(self):
        """Display keyboard shortcuts info"""
        st.info("""
        **Keyboard Shortcuts:**
        - **CMD/CTRL + K**: Open command palette
        - **D**: Data Collection
        - **T**: Trading Signals
        - **O**: Trading Operations
        - **P**: Portfolio
        - **J**: Scheduled Jobs
        - **S**: Settings
        - **L**: Action Logs
        - **A**: Auth Test
        """)

    def search(self, query: str) -> List[Dict]:
        """Search commands by name and keywords"""
        if not query:
            return self.commands

        query = query.lower()
        results = []

        for cmd in self.commands:
            # Calculate relevance score
            score = 0

            # Check name
            if query in cmd["name"].lower():
                score += 10

            # Check keywords
            for keyword in cmd["keywords"]:
                if query in keyword:
                    score += 5

            # Check category
            if query in cmd["category"].lower():
                score += 3

            if score > 0:
                results.append({"command": cmd, "score": score})

        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        return [r["command"] for r in results]

    @st.dialog("Applications", width="large")
    def render(self):
        """Render the command palette as icon grid"""

        # Custom CSS for icon grid layout
        st.markdown("""
        <style>
        /* Grid container for icons */
        div[data-testid="column"] {
            padding: 0.25rem !important;
        }

        /* Make buttons look like app icons */
        .stButton > button {
            height: 100px !important;
            padding: 0.5rem !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.5rem !important;
            border-radius: 1.25rem !important;
            background: var(--secondary-background-color) !important;
            border: none !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            background: var(--primary-color) !important;
            transform: scale(1.05) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }

        /* Icon styling */
        .stButton > button p {
            font-size: 2.5rem !important;
            margin: 0 !important;
            line-height: 1 !important;
        }

        /* Label styling */
        .stButton > button div {
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            text-align: center !important;
            line-height: 1.2 !important;
            margin-top: 0.25rem !important;
        }

        /* Search input styling */
        .stTextInput input {
            border-radius: 1.5rem !important;
            padding: 0.75rem 1.25rem !important;
            background: var(--secondary-background-color) !important;
            border: 2px solid var(--border-color) !important;
        }

        .stTextInput input:focus {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 2px var(--primary-color) !important;
            opacity: 0.2;
        }

        /* Category headers */
        .category-header {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-color);
            opacity: 0.6;
            margin: 1.5rem 0 0.75rem 0.5rem;
        }

        /* Scrollable content */
        div[data-testid="stVerticalBlock"] > div {
            max-height: 60vh;
            overflow-y: auto;
        }
        </style>
        """, unsafe_allow_html=True)

        # Search input
        query = st.text_input(
            "Search",
            value=st.session_state.get("palette_query", ""),
            placeholder="Search applications...",
            key="palette_search_input",
            label_visibility="collapsed"
        )
        st.session_state.palette_query = query

        # Search results
        results = self.search(query)

        if results:
            # Group by category
            categories = {}
            for cmd in results:
                cat = cmd["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(cmd)

            # Display results by category in grid
            for category, commands in categories.items():
                st.markdown(f'<div class="category-header">{category}</div>', unsafe_allow_html=True)

                # Create grid layout - 5 columns for icon grid
                cols_per_row = 5
                for i in range(0, len(commands), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, cmd in enumerate(commands[i:i + cols_per_row]):
                        with cols[j]:
                            # Create icon button
                            if st.button(
                                f"{cmd['icon']}\n\n{cmd['name']}",
                                key=f"cmd_{cmd['name']}_{i}_{j}",
                                use_container_width=True
                            ):
                                # Execute command and close dialog
                                st.session_state.palette_open = False
                                st.session_state.palette_query = ""
                                try:
                                    cmd["action"]()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                                st.rerun()
        else:
            st.info("No matching applications found")

        # Footer
        st.markdown("---")
        st.caption("💡 Press **CMD/CTRL + K** to close")


# Global command palette instance
_command_palette: Optional[CommandPalette] = None


def get_command_palette() -> CommandPalette:
    """Get or create the global command palette instance"""
    global _command_palette
    if _command_palette is None:
        _command_palette = CommandPalette()
    return _command_palette


def show_command_palette():
    """Show the command palette"""
    st.session_state.palette_open = True


def hide_command_palette():
    """Hide the command palette"""
    st.session_state.palette_open = False


def toggle_command_palette():
    """Toggle the command palette visibility"""
    if "palette_open" not in st.session_state:
        st.session_state.palette_open = False
    st.session_state.palette_open = not st.session_state.palette_open
