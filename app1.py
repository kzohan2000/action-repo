from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["github_webhooks"]
collection = db["actions"]

# Utility function to format timestamp
def get_utc_timestamp():
    return datetime.utcnow().strftime("%d %B %Y - %I:%M %p UTC")

# Webhook endpoint to receive GitHub events
@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json
    action_type = data.get("action")
    author = data["sender"]["login"]
    timestamp = get_utc_timestamp()

    # Common structure to insert into MongoDB
    action_data = {
        "author": author,
        "action": action_type,
        "timestamp": timestamp
    }

    # Handle different GitHub events
    if "push" in data:  # Handling PUSH actions
        commit_hash = data["head_commit"]["id"]  # Request ID for Push
        branch = data["ref"].split("/")[-1]  # Get the branch name (to_branch)
        action_data.update({
            "request_id": commit_hash,
            "to_branch": branch
        })
    
    elif "pull_request" in data:  # Handling PULL_REQUEST actions
        pr_data = data["pull_request"]
        pr_id = pr_data["id"]  # Pull Request ID
        from_branch = pr_data["head"]["ref"]
        to_branch = pr_data["base"]["ref"]
        action_data.update({
            "request_id": pr_id,
            "from_branch": from_branch,
            "to_branch": to_branch
        })

        # If the pull request is merged, treat it as a merge action
        if action_type == "closed" and pr_data["merged"]:
            action_data["action"] = "merge"

    # Insert the action data into MongoDB
    collection.insert_one(action_data)

    return jsonify({"status": "success", "data": action_data}), 200


# Endpoint to get the latest actions from MongoDB for the UI
@app.route("/latest-actions", methods=["GET"])
def latest_actions():
    # Retrieve the 10 most recent actions from MongoDB
    actions = list(collection.find().sort("timestamp", -1).limit(10))
    return jsonify(actions), 200


if __name__ == "__main__":
    app.run(port=5000)
