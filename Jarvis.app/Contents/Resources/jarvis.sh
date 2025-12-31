#!/usr/bin/env bash
# JARVIS - simple macOS assistant (installed at ~/AgentSites/Jarvis)
USER_NAME="sjpenn"
BASE_DIR="$HOME/AgentSites/Jarvis"

# Speak text using macOS say + Notification (formal voice)
function speak_notify() {
  local text="$1"
  /usr/bin/say -v Samantha "$text" &
  /usr/bin/osascript -e "display notification \"${text//\"/\\\"}\" with title \"JARVIS\" subtitle \"$USER_NAME\""
}

# Show system status summary
function status() {
  uptime=$(uptime | sed 's/,//g')
  mem=$(vm_stat | awk -F: '/Pages free|Pages active|Pages inactive/ {printf "%s: %s\n",$1,$2}')
  battery=$(pmset -g batt | awk 'NR==2{gsub(/;/,""); print $3, $4}')
  disk=$(df -h / | awk 'NR==2{print $3 " used of " $2}')
  speak_notify "System status: $uptime. Battery $battery. Disk $disk."
  printf "Uptime: %s\n\nMemory:\n%s\n\nBattery: %s\nDisk: %s\n" "$uptime" "$mem" "$battery" "$disk"
}

# Read next calendar events (uses AppleScript to query macOS Calendar)
function next_events() {
  /usr/bin/osascript <<'APLS'
  tell application "Calendar"
    set nowDate to current date
    set endDate to nowDate + (24 * hours)
    set eventList to {}
    repeat with c in calendars
      set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
      repeat with e in evs
        set end of eventList to (summary of e & " — " & start date of e as string)
      end repeat
    end repeat
    if (count of eventList) = 0 then
      return "No events in the next 24 hours."
    else
      return eventList as string
    end if
  end tell
APLS
}

# Email notification (opens Mail compose window with subject/body)
function compose_email() {
  local to="$1"; shift
  local subj="$1"; shift
  local body="$*"
  /usr/bin/osascript <<APLS
  tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"$subj", content:"$body", visible:true}
    tell newMessage
      make new to recipient at end of to recipients with properties {address:"$to"}
      activate
    end tell
  end tell
APLS
}

# Help
function help_text() {
  cat <<EOF
JARVIS CLI - usage:
  $BASE_DIR/jarvis.sh status                # speak + print system status
  $BASE_DIR/jarvis.sh events                # list next 24h calendar events
  $BASE_DIR/jarvis.sh say "Text to speak"   # speak + notify
  $BASE_DIR/jarvis.sh email TO SUBJECT BODY # open Mail compose
  $BASE_DIR/jarvis.sh help                  # show this help
EOF
}

# Self-update helper (copy new files into place if provided)
function install_files() {
  echo "Ensuring directory exists: $BASE_DIR"
  mkdir -p "$BASE_DIR"
  # nothing else — files should already be in place
}

# Dispatch
case "$1" in
  status) status ;;
  events) next_events ;;
  say) shift; speak_notify "$*" ;;
  email) shift; compose_email "$@" ;;
  help|'' ) help_text ;;
  install) install_files ;;
  *) echo "Unknown command. Run $BASE_DIR/jarvis.sh help" ;;
esac
