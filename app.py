import json
import os
import re
import time
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")

app.secret_key = os.getenv("SECRET_KEY", "hivebuzz-secret-key-change-this")
API_URL = os.getenv("API_URL", "https://api.hive.blog")
DBUZZ_API_URL = os.getenv("DBUZZ_API_URL", "https://api.dbuzz.com")

# In-memory storage for demo posts
demo_posts = [
    {
        "id": 1,
        "author": "demo_user",
        "title": "Hello Hive World",
        "body": "This is a sample post from HiveBuzz application.",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "permlink": "hello-hive-world",
        "tags": ["hivebuzz", "demo", "hello"],
    },
    {
        "id": 2,
        "author": "test_account",
        "title": "Welcome to HiveBuzz",
        "body": "HiveBuzz is a decentralized social media app on Hive blockchain.",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "permlink": "welcome-to-hivebuzz",
        "tags": ["hivebuzz", "welcome", "blockchain"],
    },
]


# Utility functions
def generate_permlink():
    """Generate a random permlink"""
    import random
    import string

    possible = string.ascii_lowercase + string.digits
    return "".join(random.choice(possible) for _ in range(16))


def format_tag(tag):
    """Format a tag for use with the blockchain"""
    if not tag:
        return ""
    # Remove spaces and special characters, convert to lowercase
    tag = tag.strip().lower()
    tag = re.sub(r"\s+", "-", tag)
    tag = re.sub(r"[^a-z0-9-]", "", tag)
    return tag if tag else ""


def sanitize_content(content):
    """Basic content sanitization"""
    if not content:
        return ""
    # You could add more sophisticated sanitization here
    return content.strip()


# Routes
@app.route("/")
def index():
    """Main page route"""
    if "username" in session:
        return render_template("dashboard.html", username=session["username"])
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    """Handle login submission - in a real app, this would verify with Hive blockchain"""
    username = request.form.get("username")
    signature = request.form.get("signature")
    challenge = request.form.get("challenge")
    if not all([username, signature, challenge]):
        flash("Missing required authentication data", "error")
        return redirect(url_for("index"))
    session["username"] = username
    flash(f"Welcome, {username}!", "success")
    return redirect(url_for("index"))


@app.route("/login-hiveauth", methods=["POST"])
def login_hiveauth():
    """Handle HiveAuth login submission"""
    username = request.form.get("username")
    auth_token = request.form.get("auth_token")
    uuid = request.form.get("uuid")
    if not all([username, auth_token, uuid]):
        flash("Invalid authentication data", "error")
        return redirect(url_for("index"))
    session["username"] = username
    session["auth_method"] = "hiveauth"
    flash(f"Welcome, {username}! Authenticated with HiveAuth", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Clear user session"""
    username = session.pop("username", None)
    session.pop("auth_method", None)
    if username:
        flash(f"Goodbye, {username}!", "info")
    return redirect(url_for("index"))


@app.route("/posts")
def posts():
    """Fetch and display posts from Hive blockchain or memory storage"""
    try:
        try:
            response = requests.get(
                f"{DBUZZ_API_URL}/posts",
                params={"limit": 10},
                headers={"Accept": "application/json"},
                timeout=5,
            )
            api_posts = response.json()
            all_posts = api_posts + demo_posts
            all_posts.sort(key=lambda x: x.get("created", ""), reverse=True)
        except Exception as e:
            print(f"API error: {str(e)}")
            all_posts = sorted(
                demo_posts, key=lambda x: x.get("created", ""), reverse=True
            )
        return render_template("posts.html", posts=all_posts, now=datetime.now())
    except Exception as e:
        return render_template("error.html", error=str(e), now=datetime.now())


@app.route("/post/<author>/<permlink>")
def view_post(author, permlink):
    """View a single post in detail"""
    try:
        post = next(
            (
                p
                for p in demo_posts
                if p["author"] == author and p["permlink"] == permlink
            ),
            None,
        )
        if not post:
            try:
                response = requests.post(
                    API_URL,
                    json={
                        "jsonrpc": "2.0",
                        "method": "condenser_api.get_content",
                        "params": [author, permlink],
                        "id": 1,
                    },
                    headers={"Content-Type": "application/json"},
                )
                data = response.json()
                if "result" in data and data["result"].get("author") == author:
                    post = data["result"]
            except Exception as e:
                print(f"Error fetching post from blockchain: {e}")
        if post:
            return render_template("post_detail.html", post=post, now=datetime.now())
        else:
            return render_template(
                "error.html", error="Post not found", now=datetime.now()
            )
    except Exception as e:
        return render_template("error.html", error=str(e), now=datetime.now())


@app.route("/profile/<username>")
def profile(username):
    """Display user profile from Hive blockchain"""
    try:
        response = requests.post(
            API_URL,
            json={
                "jsonrpc": "2.0",
                "method": "condenser_api.get_accounts",
                "params": [[username]],
                "id": 1,
            },
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        if "result" in data and len(data["result"]) > 0:
            user_data = data["result"][0]
            metadata = {}
            try:
                if user_data.get("json_metadata"):
                    metadata = json.loads(user_data["json_metadata"])
            except:
                pass
            recent_posts = []
            try:
                posts_response = requests.post(
                    API_URL,
                    json={
                        "jsonrpc": "2.0",
                        "method": "condenser_api.get_discussions_by_blog",
                        "params": [{"tag": username, "limit": 5}],
                        "id": 2,
                    },
                    headers={"Content-Type": "application/json"},
                )
                posts_data = posts_response.json()
                if "result" in posts_data:
                    recent_posts = posts_data["result"]
            except Exception as e:
                print(f"Error fetching recent posts: {e}")
            return render_template(
                "profile.html",
                user=user_data,
                metadata=metadata,
                recent_posts=recent_posts,
                now=datetime.now(),
            )
        else:
            return render_template(
                "error.html", error="User not found", now=datetime.now()
            )
    except Exception as e:
        return render_template("error.html", error=str(e), now=datetime.now())


@app.route("/create", methods=["GET", "POST"])
def create_post():
    """Create post form and submission handler"""
    if "username" not in session:
        flash("You must be logged in to create a post.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")
        tags_string = request.form.get("tags", "")
        raw_tags = [t.strip() for t in tags_string.split(",") if t.strip()]
        tags = [format_tag(tag) for tag in raw_tags]
        tags = [tag for tag in tags if tag]
        if not tags:
            tags = ["hivebuzz"]
        permlink = "-".join(format_tag(word) for word in title.lower().split())  # type: ignore
        if not permlink:
            permlink = generate_permlink()
        new_post = {
            "id": len(demo_posts) + 1,
            "author": session["username"],
            "title": title,
            "body": body,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "permlink": permlink,
            "tags": tags,
        }
        demo_posts.append(new_post)
        flash("Post created successfully!", "success")
        return redirect(url_for("posts"))
    return render_template("create_post.html", now=datetime.now())


@app.route("/api/get_account_info/<username>")
def get_account_info(username):
    """API endpoint to get account info"""
    try:
        response = requests.post(
            API_URL,
            json={
                "jsonrpc": "2.0",
                "method": "condenser_api.get_accounts",
                "params": [[username]],
                "id": 1,
            },
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        if "result" in data and len(data["result"]) > 0:
            return jsonify(data["result"][0])
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/trending")
def trending():
    """Fetch trending posts from Hive blockchain"""
    try:
        response = requests.post(
            API_URL,
            json={
                "jsonrpc": "2.0",
                "method": "condenser_api.get_discussions_by_trending",
                "params": [{"tag": "", "limit": 10}],
                "id": 1,
            },
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        trending_posts = data["result"] if "result" in data else []
        if not trending_posts:
            trending_posts = [
                {
                    "id": 101,
                    "author": "hivetrending",
                    "title": "Why Hive is the Future of Social Media",
                    "body": "Hive blockchain offers a censorship-resistant platform for content creators...",
                    "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "permlink": "why-hive-is-the-future",
                    "tags": ["hive", "blockchain", "crypto", "social"],
                },
                {
                    "id": 102,
                    "author": "cryptoanalyst",
                    "title": "The Rise of Web3 Social Networks",
                    "body": "Decentralized social networks are changing how we connect online...",
                    "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "permlink": "web3-social-networks",
                    "tags": ["web3", "defi", "social", "blockchain"],
                },
            ]
        return render_template(
            "trending.html", posts=trending_posts, now=datetime.now()
        )
    except Exception as e:
        return render_template("error.html", error=str(e), now=datetime.now())


@app.context_processor
def inject_now():
    return {"now": datetime.now()}


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", now=datetime.now()), 404


@app.errorhandler(500)
def internal_server_error(e):
    return (
        render_template(
            "error.html", error="Internal server error", now=datetime.now()
        ),
        500,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
