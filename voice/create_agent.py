"""Create the ElevenLabs voice agent for the dashboard.

    ELEVENLABS_API_KEY=... python voice/create_agent.py          # creates the agent, prints its id
    python voice/create_agent.py dump                            # prints the configuration, no API call

The agent has no server side: its eight tools are client tools that run in the
dashboard page. Pass the printed agent id to the dashboard build with --voice-agent.
Conversations are billed by ElevenLabs. The agent is public: anyone who has the id can
talk to it, so do not publish a dashboard built with --voice-agent without thinking about that.
"""
import json, os, sys, urllib.request
PROMPT = """# Personality
You are the voice of a building operations desk. You are calm, exact and brief, like an experienced control-room operator.

# Environment
You speak with an operator who looks at a dashboard for PLATO-40, a fictional 40-room self-check-in hotel. All data is synthetic and a year of it is replayed. The dashboard is on the operator's screen and you control it with your tools. You know nothing about the building except what your tools return. All times are Vienna local time.

# Tone
- Two or three short sentences per turn. Numbers first.
- Say room and asset names clearly, for example "room R 4 0 3" or "heat pump H P 1".
- No filler, no apologies, no lists longer than three items unless asked.
- Never read identifiers such as event ids aloud.

# Goal
Help the operator see the status and decide on approvals.
1. For a status question call get_status and summarise it.
2. To show something call open_view or open_case, then say in one sentence what is on screen.
3. For approvals call list_pending_approvals and read the items with their number, action, asset and risk.
4. Before approve or reject, repeat the item in one sentence and ask "Shall I approve?" or "Shall I reject?". Call the tool only after a clear yes. One item at a time. This step is important.
5. If an item needs guest consent, say so. Call record_guest_consent only when the operator states that the guest's consent is on record. Never assume consent. This step is important.
6. After a tool call, report exactly what the tool returned. If it returned an error, say the error.

# Guardrails
- You never decide on your own. Approving, rejecting and recording consent happen only on the operator's explicit word.
- Everything is a simulation. Say "approved in the simulation", never that something was really done, dispatched or repaired.
- Do not invent rooms, numbers, times or cases. If a tool returns nothing, say that nothing was found.
- If asked about anything other than this building's operation, say that you only handle PLATO-40 operations.
- PLATO-40 is fictional. Nothing you say is a statement about real PLATO buildings or about CLARA.
"""
def tool(name, description, properties=None, required=None):
    return {"type": "client", "name": name, "description": description, "expects_response": True, "response_timeout_secs": 10,
            "parameters": {"type": "object", "properties": properties or {}, "required": required or []}}
ITEM = {"item": {"type": "integer", "description": "Number of the item as returned by list_pending_approvals, starting at 1"}}
TOOLS = [
    tool("get_status", "Current status of the building: number of cases per scenario, how many decisions wait for a person, and the most urgent open items."),
    tool("open_view", "Switch the dashboard to a view.", {"view": {"type": "string", "enum": ["overview", "turnaround", "water", "heating", "maintenance", "weekend", "energy", "logistics", "approvals", "decisions"], "description": "The view to show"}}, ["view"]),
    tool("open_case", "Find a case and show it on the dashboard. Returns its title, time, risk and what was decided.", {"query": {"type": "string", "description": "Words to search for, such as a room like R403, 'heat pump', 'filter', 'water leak', a date like 2026-07-17, or a booking number"}}, ["query"]),
    tool("describe_current_case", "Details of the case that is currently open on the dashboard: evidence, decisions, autonomy level and the later work order if there is one."),
    tool("list_pending_approvals", "The decisions that wait for a person, most urgent first, numbered from 1. Call this before approving or rejecting.", {"limit": {"type": "integer", "description": "How many items to return, 1 to 10. Default 3."}}),
    tool("record_guest_consent", "Record that the guest's consent is on record for an item that needs it. Only on the operator's explicit statement.", ITEM, ["item"]),
    tool("approve", "Approve one pending item. Only after the operator confirmed with a clear yes. Fails if guest consent is required and not on record.", ITEM, ["item"]),
    tool("reject", "Reject one pending item. Only after the operator confirmed with a clear yes.", ITEM, ["item"]),
]
body = {
    "name": "HOIV Building Ops Voice",
    "conversation_config": {
        "agent": {
            "first_message": "Building operations for PLATO-40. Ask me for the status, a case, or the approval queue.",
            "language": "en",
            "prompt": {"prompt": PROMPT, "llm": "gemini-2.5-flash", "temperature": 0.2, "timezone": "Europe/Vienna",
                       "tools": TOOLS},
        },
        "tts": {"voice_id": "JBFqnCBsd6RMkjVDRZzb"},
        "conversation": {"max_duration_seconds": 300},
    },
    # The widget wears the dashboard's style set (dark card, blue primary button, 8 px radius).
    "platform_settings": {"widget": {
        "bg_color": "#181e29", "text_color": "#eef1f6", "btn_color": "#508cdc", "btn_text_color": "#0a0e15", "border_color": "#2c3442",
        "focus_color": "#508cdc", "border_radius": 8, "btn_radius": 8, "avatar": {"type": "orb", "color_1": "#508cdc", "color_2": "#9cc3f0"},
        "text_contents": {"main_label": "Talk to the building", "start_call": "Start voice", "end_call": "End", "start_chat": "Type instead"},
        "styles": {"base": "#181e29", "base_hover": "#222a38", "base_active": "#2a3344", "base_border": "#2c3442", "base_subtle": "#9aa3b2",
                   "base_primary": "#eef1f6", "accent": "#508cdc", "accent_hover": "#6aa0e6", "accent_active": "#3f7bcb", "accent_border": "#508cdc",
                   "accent_primary": "#0a0e15", "button_radius": 8, "input_radius": 8, "bubble_radius": 8, "sheet_radius": 8}}},
}
if len(sys.argv) > 1 and sys.argv[1] == "dump":
    print(json.dumps(body, indent=1)); sys.exit()
req = urllib.request.Request("https://api.elevenlabs.io/v1/convai/agents/create", data=json.dumps(body).encode(),
                             headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"})
try:
    print(urllib.request.urlopen(req, timeout=60).read().decode()[:400])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:1500])
