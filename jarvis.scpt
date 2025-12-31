-- JARVIS AppleScript helper
-- Save this as jarvis.scpt and optionally compile into an app via Script Editor
on run
  display dialog "What should JARVIS say?" default answer ""
  set theText to text returned of result
  do shell script "/usr/bin/say -v Samantha " & quoted form of theText & " & /usr/bin/osascript -e " & quoted form of "display notification " & quoted form of theText & " with title \"JARVIS\""
end run
