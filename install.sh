#!/usr/bin/env bash
# install.sh - set permissions, create zsh alias, and give basic instructions
BASE="$HOME/AgentSites/Jarvis"
JARVIS_SH="$BASE/jarvis.sh"

mkdir -p "$BASE"
chmod +x "$JARVIS_SH"

# Add alias to ~/.zshrc if not present
if ! grep -qxF "alias jarvis=\"$JARVIS_SH\"" ~/.zshrc 2>/dev/null; then
  echo "alias jarvis=\"$JARVIS_SH\"" >> ~/.zshrc
  echo "Added alias to ~/.zshrc. Run: source ~/.zshrc or open a new terminal."
else
  echo "Alias already present in ~/.zshrc"
fi

echo "Installation complete. Run: jarvis help"
