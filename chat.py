"""
Multi-provider terminal chat.
Commands (type inside the chat):
  /claude [model]   — switch to Claude  (default: claude-sonnet-4-6)
  /z.ai [model]     — switch to z.ai    (default: glm-4-flash)
  /models           — list models for current provider
  /clear            — wipe conversation history
  /help             — show this list
  /exit             — quit
"""

import os, sys, textwrap
from typing import Optional

try:
    import anthropic
except ImportError:
    sys.exit("Missing: py -m pip install anthropic")

try:
    from openai import OpenAI
except ImportError:
    sys.exit("Missing: py -m pip install openai")

# ── ANSI colours ────────────────────────────────────────────────────────────
R = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
CYAN  = "\033[96m"
PURPLE = "\033[95m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
GREY   = "\033[90m"

# Enable ANSI on Windows
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)

# ── Model catalogues ────────────────────────────────────────────────────────
CLAUDE_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-8",
    "claude-haiku-4-5-20251001",
    "claude-fable-5",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
]

ZAI_MODELS = [
    "glm-4-flash",
    "glm-4-air",
    "glm-4",
    "glm-4-plus",
    "glm-4-long",
    "glm-z1-flash",
    "glm-z1-air",
    "glm-z1-airx",
]

ZAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

# ── State ────────────────────────────────────────────────────────────────────
provider  = "claude"
model     = "claude-sonnet-4-6"
history: list[dict] = []

def provider_tag() -> str:
    if provider == "claude":
        return f"{CYAN}{BOLD}[claude/{model}]{R}"
    return f"{PURPLE}{BOLD}[z.ai/{model}]{R}"

def print_help():
    print(f"""
{BOLD}Commands:{R}
  {YELLOW}/claude [model]{R}   switch to Claude   (current: {CYAN}{model if provider=='claude' else CLAUDE_MODELS[0]}{R})
  {YELLOW}/z.ai [model]{R}     switch to z.ai     (current: {PURPLE}{model if provider=='z.ai' else ZAI_MODELS[0]}{R})
  {YELLOW}/models{R}           list models for current provider
  {YELLOW}/clear{R}            wipe conversation history
  {YELLOW}/help{R}             show this message
  {YELLOW}/exit{R}             quit
""")

def list_models():
    if provider == "claude":
        print(f"\n{CYAN}Claude models:{R}")
        for m in CLAUDE_MODELS:
            star = f" {GREEN}← active{R}" if m == model else ""
            print(f"  {m}{star}")
    else:
        print(f"\n{PURPLE}z.ai models:{R}")
        for m in ZAI_MODELS:
            star = f" {GREEN}← active{R}" if m == model else ""
            print(f"  {m}{star}")
    print()

def stream_claude(user_msg: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"{RED}Set ANTHROPIC_API_KEY environment variable.{R}")
        return ""
    client = anthropic.Anthropic(api_key=api_key)
    msgs = history + [{"role": "user", "content": user_msg}]
    full = ""
    print(f"\n{CYAN}Claude:{R} ", end="", flush=True)
    with client.messages.stream(model=model, max_tokens=8096, messages=msgs) as s:
        for text in s.text_stream:
            print(text, end="", flush=True)
            full += text
    print()
    return full

def stream_zai(user_msg: str) -> str:
    api_key = os.environ.get("ZAI_API_KEY") or os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print(f"{RED}Set ZAI_API_KEY environment variable.{R}")
        return ""
    client = OpenAI(api_key=api_key, base_url=ZAI_BASE_URL)
    msgs = history + [{"role": "user", "content": user_msg}]
    full = ""
    print(f"\n{PURPLE}z.ai:{R} ", end="", flush=True)
    stream = client.chat.completions.create(model=model, messages=msgs, stream=True)
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        print(delta, end="", flush=True)
        full += delta
    print()
    return full

def handle_command(cmd: str) -> bool:
    """Return True if the input was a command (skip adding to history)."""
    global provider, model

    parts = cmd.strip().split(None, 1)
    name  = parts[0].lower()
    arg   = parts[1].strip() if len(parts) > 1 else ""

    if name == "/exit":
        print(f"\n{DIM}bye{R}")
        sys.exit(0)

    if name == "/help":
        print_help()
        return True

    if name == "/models":
        list_models()
        return True

    if name == "/clear":
        history.clear()
        print(f"{DIM}history cleared{R}")
        return True

    if name == "/claude":
        provider = "claude"
        model    = arg if arg else CLAUDE_MODELS[0]
        print(f"{DIM}→ switched to {provider_tag()}{R}")
        return True

    if name == "/z.ai":
        provider = "z.ai"
        model    = arg if arg else ZAI_MODELS[0]
        print(f"{DIM}→ switched to {provider_tag()}{R}")
        return True

    return False

def chat(user_msg: str):
    if provider == "claude":
        reply = stream_claude(user_msg)
    else:
        reply = stream_zai(user_msg)
    if reply:
        history.append({"role": "user",      "content": user_msg})
        history.append({"role": "assistant",  "content": reply})

# ── Main loop ────────────────────────────────────────────────────────────────
def main():
    print(f"""
{BOLD}Multi-provider chat{R}  {GREY}(type /help for commands){R}
Starting with {provider_tag()}
""")
    while True:
        try:
            prompt = input(f"{provider_tag()} {BOLD}>{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}bye{R}")
            sys.exit(0)

        if not prompt:
            continue

        if prompt.startswith("/"):
            if not handle_command(prompt):
                print(f"{RED}Unknown command. Type /help for the list.{R}")
        else:
            chat(prompt)

if __name__ == "__main__":
    main()
