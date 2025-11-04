"""
Command Palette for Politician Trading Tracker
Provides CMD+K / CTRL+K searchable interface for all app features
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
            "Go to Data Collection",
            lambda: st.switch_page("1_📥_Data_Collection.py"),
            category="Navigation",
            keywords=["data", "collection", "fetch", "scrape", "download"],
            icon="📥"
        )

        self.add_command(
            "Go to Trading Signals",
            lambda: st.switch_page("2_🎯_Trading_Signals.py"),
            category="Navigation",
            keywords=["signals", "trading", "buy", "sell", "recommendations"],
            icon="🎯"
        )

        self.add_command(
            "Go to Trading Operations",
            lambda: st.switch_page("3_💼_Trading_Operations.py"),
            category="Navigation",
            keywords=["operations", "trade", "execute", "orders"],
            icon="💼"
        )

        self.add_command(
            "Go to Portfolio",
            lambda: st.switch_page("4_📈_Portfolio.py"),
            category="Navigation",
            keywords=["portfolio", "holdings", "positions", "performance"],
            icon="📈"
        )

        self.add_command(
            "Go to Scheduled Jobs",
            lambda: st.switch_page("5_⏰_Scheduled_Jobs.py"),
            category="Navigation",
            keywords=["jobs", "scheduled", "automation", "cron", "tasks"],
            icon="⏰"
        )

        self.add_command(
            "Go to Settings",
            lambda: st.switch_page("6_⚙️_Settings.py"),
            category="Navigation",
            keywords=["settings", "config", "configuration", "preferences"],
            icon="⚙️"
        )

        self.add_command(
            "Go to Database Setup",
            lambda: st.switch_page("7_🔧_Database_Setup.py"),
            category="Navigation",
            keywords=["database", "setup", "schema", "tables", "migration"],
            icon="🔧"
        )

        self.add_command(
            "Go to Action Logs",
            lambda: st.switch_page("8_📋_Action_Logs.py"),
            category="Navigation",
            keywords=["logs", "actions", "history", "audit", "events"],
            icon="📋"
        )

        self.add_command(
            "Go to Auth Test",
            lambda: st.switch_page("99_🧪_Auth_Test.py"),
            category="Navigation",
            keywords=["auth", "authentication", "test", "login", "session"],
            icon="🧪"
        )

        # Feature commands
        self.add_command(
            "Refresh Data",
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
            "View Keyboard Shortcuts",
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

    def render(self):
        """Render the command palette UI"""

        # Initialize session state for palette
        if "palette_open" not in st.session_state:
            st.session_state.palette_open = False
        if "palette_query" not in st.session_state:
            st.session_state.palette_query = ""
        if "palette_selected" not in st.session_state:
            st.session_state.palette_selected = None

        # Only show if palette is open
        if st.session_state.palette_open:
            # Create modal-like container
            with st.container():
                st.markdown("""
                <style>
                .command-palette {
                    position: fixed;
                    top: 20%;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 9999;
                    background: var(--background-color);
                    border: 2px solid var(--primary-color);
                    border-radius: 0.75rem;
                    padding: 1rem;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    width: 600px;
                    max-width: 90vw;
                }
                </style>
                """, unsafe_allow_html=True)

                st.markdown("### 🔍 Command Palette")
                st.caption("Search for pages and actions")

                # Search input
                query = st.text_input(
                    "Search",
                    value=st.session_state.palette_query,
                    placeholder="Type to search...",
                    key="palette_search_input",
                    label_visibility="collapsed"
                )
                st.session_state.palette_query = query

                # Search results
                results = self.search(query)

                if results:
                    st.markdown("---")

                    # Group by category
                    categories = {}
                    for cmd in results[:10]:  # Limit to top 10 results
                        cat = cmd["category"]
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(cmd)

                    # Display results by category
                    for category, commands in categories.items():
                        st.markdown(f"**{category}**")

                        for cmd in commands:
                            col1, col2 = st.columns([0.9, 0.1])

                            with col1:
                                if st.button(
                                    f"{cmd['icon']} {cmd['name']}",
                                    key=f"cmd_{cmd['name']}",
                                    use_container_width=True
                                ):
                                    # Execute command
                                    st.session_state.palette_open = False
                                    st.session_state.palette_query = ""
                                    try:
                                        cmd["action"]()
                                    except Exception as e:
                                        st.error(f"Error executing command: {e}")
                                    st.rerun()

                        st.markdown("")
                else:
                    st.info("No matching commands found")

                # Close button
                if st.button("✕ Close", use_container_width=True):
                    st.session_state.palette_open = False
                    st.session_state.palette_query = ""
                    st.rerun()


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
