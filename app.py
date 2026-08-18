import os
import re
import urllib.parse
import urllib.request

from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)


def get_vid(query):
    """Search YouTube and return the first video ID found."""
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        # Extract YouTube video IDs from the page.
        ids = re.findall(r'"videoId":"([^"]+)"', data)

        return ids[0] if ids else None

    except Exception as e:
        print(f"YouTube search error: {e}")
        return None


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():
    data = request.get_json(silent=True)

    if not data:
        abort(400, description="Invalid JSON request")

    if "command" not in data and "text_command" not in data:
        abort(400, description="Missing command")

    command_raw = data.get("command") or data.get("text_command")

    if not isinstance(command_raw, str):
        abort(400, description="Command must be a string")

    command = command_raw.strip().lower()

    if not command:
        abort(400, description="Command cannot be empty")

    target = None
    message = "Command not recognized"

    # =========================================================
    # YOUTUBE COMMAND
    # =========================================================
    if "youtube" in command:
        query = command

        patterns = [
            "open youtube and search",
            "open youtube and play",
            "search youtube for",
            "search youtube",
            "open youtube",
            "and play",
            "play",
            "on youtube",
        ]

        for pattern in patterns:
            query = query.replace(pattern, "")

        query = query.strip()

        if not query:
            return jsonify({
                "success": False,
                "message": "Please specify what you want to search on YouTube.",
                "url": None
            }), 400

        video_id = get_vid(query)

        if video_id:
            target = (
                f"https://www.youtube.com/embed/"
                f"{video_id}?autoplay=1&mute=1"
            )

            message = f"Playing {query}"

        else:
            message = f"No YouTube video found for: {query}"

    # =========================================================
    # GMAIL / EMAIL COMMAND
    # =========================================================
    elif any(
        keyword in command
        for keyword in ["gmail", "email", "mail", "message"]
    ):
        to = ""
        body = ""

        # Remove command prefix.
        clean_command = re.sub(
            r"^(please\s+)?(open\s+)?"
            r"(gmail|email|mail|message)\s*",
            "",
            command,
            flags=re.IGNORECASE
        ).strip()

        # Remove optional command words.
        clean_command = re.sub(
            r"\b(command|com)\b",
            "",
            clean_command,
            flags=re.IGNORECASE
        ).strip()

        # Separate recipient from message body.
        parts = re.split(
            r"\b(type|write|saying|message|content|with body)\b",
            clean_command,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        recipient_part = parts[0].strip()

        # Remove phrases before recipient.
        recipient_part = re.sub(
            r"^(update\s+to|to|send\s+to|and\s+update)\s*",
            "",
            recipient_part,
            flags=re.IGNORECASE
        ).strip()

        # Get email body.
        if len(parts) > 1:
            body = parts[-1].strip()

        # Convert spoken email format:
        # john at gmail dot com
        if recipient_part:
            email = recipient_part

            email = re.sub(
                r"\s+at\s+",
                "@",
                email,
                flags=re.IGNORECASE
            )

            email = re.sub(
                r"\s+dot\s+",
                ".",
                email,
                flags=re.IGNORECASE
            )

            # Remove unwanted characters.
            email = re.sub(
                r"[^a-zA-Z0-9@._%+\-]",
                "",
                email
            )

            # If user only supplied a username,
            # assume Gmail.
            if "@" in email:
                to = email
            elif email:
                to = f"{email}@gmail.com"

        # Gmail compose URL.
        base_url = (
            "https://mail.google.com/mail/u/0/"
            "?view=cm&fs=1"
        )

        params = urllib.parse.urlencode({
            "to": to,
            "body": body
        })

        target = f"{base_url}&{params}"

        if to:
            message = f"Drafting email to {to}"
        else:
            message = "Opening Gmail compose window"

    # =========================================================
    # UNKNOWN COMMAND
    # =========================================================
    else:
        return jsonify({
            "success": False,
            "message": "Command not recognized",
            "url": None
        }), 400

    # =========================================================
    # RESPONSE
    # =========================================================
    return jsonify({
        "success": True,
        "message": message,
        "url": target
    })


# =============================================================
# RUN SERVER
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
