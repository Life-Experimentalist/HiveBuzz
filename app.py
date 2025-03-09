import logging
import os
import random
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Blueprint,
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import database as db  # Import our database module
from config import get_config
from session_manager import session_manager  # Import our session manager
from utils.auth_manager import AuthManager  # Import auth manager
from utils.hiveauth import get_hiveauth_verifier, init_hiveauth

# Import our HiveSigner and HiveAuth utils
from utils.hivesigner import get_hivesigner_client, init_hivesigner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get config based on environment
config = get_config()

app = Flask(__name__)
app.config.from_object(config)

# Add additional configuration from .env file directly to app config
app.config["HIVESIGNER_APP_NAME"] = os.getenv("HIVESIGNER_APP_NAME", "HiveBuzz")
app.config["HIVESIGNER_REDIRECT_URI"] = os.getenv(
    "HIVESIGNER_REDIRECT_URI", "http://localhost:5000/hivesigner/callback"
)
app.config["HIVESIGNER_APP_HOST"] = os.getenv(
    "HIVESIGNER_APP_HOST", "https://hivesigner.com"
)
app.config["APP_URL"] = os.getenv("APP_URL", "http://localhost:5000")

# Initialize session manager with the app
session_manager.init_app(app)

# Initialize auth manager
auth_manager = AuthManager(app)

# Initialize HiveSigner with app details from .env
hivesigner_app_name = app.config["HIVESIGNER_APP_NAME"]
hivesigner_client_secret = os.getenv("HIVESIGNER_CLIENT_SECRET", "")
init_hivesigner(client_id=hivesigner_app_name, client_secret=hivesigner_client_secret)

# Initialize HiveAuth with app details from .env
init_hiveauth(
    app_name=app.config["HIVESIGNER_APP_NAME"],
    app_description=f"{app.config['HIVESIGNER_APP_NAME']} - Explore the Hive blockchain",
    app_icon=f"{app.config['APP_URL']}/static/img/logo.svg",
)

# Demo data for non-authenticated views
DEMO_POSTS = [
    {
        "id": 1,
        "author": "demo",
        "permlink": "welcome-to-hivebuzz",
        "title": "Welcome to HiveBuzz",
        "body": "This is a demo post to show what HiveBuzz looks like. In a real deployment, this would be actual content from the Hive blockchain.",
        "created": "2023-05-15T10:30:00",
        "payout": "10.52",
        "tags": ["hivebuzz", "welcome", "demo"],
        "vote_count": 42,
        "comment_count": 7,
    },
    {
        "id": 2,
        "author": "demo",
        "permlink": "getting-started-with-hive",
        "title": "Getting Started with Hive Blockchain",
        "body": "Hive is a fast, scalable, and powerful blockchain built for Web 3.0. This post introduces you to the basics of Hive and how to get started.",
        "created": "2023-05-10T08:15:00",
        "payout": "25.75",
        "tags": ["hive", "blockchain", "crypto", "tutorial"],
        "vote_count": 67,
        "comment_count": 15,
    },
    {
        "id": 3,
        "author": "demo",
        "permlink": "hivebuzz-new-features",
        "title": "New Features in HiveBuzz",
        "body": "We are excited to announce several new features in HiveBuzz including improved wallet integration, better post discovery, and enhanced social features.",
        "created": "2023-05-05T14:45:00",
        "payout": "18.34",
        "tags": ["hivebuzz", "update", "features"],
        "vote_count": 53,
        "comment_count": 9,
    },
]


# Authentication required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def load_user():
    """Load user data into g if logged in"""
    if "username" in session:
        g.user = db.get_user(session["username"])
    else:
        g.user = None


@app.route("/")
def index():
    """Homepage route"""
    if "username" in session:
        # Get real user data from the database
        user_data = db.get_user(session["username"])

        # Log this page visit
        db.log_user_activity(session["username"], "page_view", {"page": "index"})

        # Get user activity for the dashboard
        activity = db.get_user_activity(session["username"], limit=5)
        formatted_activity = []

        for item in activity:
            if item["action_type"] == "page_view":
                page = item["details"].get("page", "unknown")
                formatted_activity.append(
                    {
                        "type": "view",
                        "title": f"Viewed {page} page",
                        "time": item["created_at"],
                        "link": f"/{page}" if page != "index" else "/",
                    }
                )
            elif item["action_type"] == "post_view":
                formatted_activity.append(
                    {
                        "type": "post",
                        "title": f'Viewed post: {item["details"].get("title", "Untitled")}',
                        "time": item["created_at"],
                        "link": f'/post/{item["details"].get("author")}/{item["details"].get("permlink")}',
                    }
                )
            elif item["action_type"] == "auth":
                formatted_activity.append(
                    {
                        "type": "auth",
                        "title": f'Authentication: {item["details"].get("action", "login")}',
                        "time": item["created_at"],
                    }
                )

        # Fetch some trending posts (using demo data for now)
        # In real app, this would come from the Hive API
        trending_posts = DEMO_POSTS[:3]

        return render_template(
            "dashboard.html",
            user=user_data,
            stats={
                "wallet": {"hive": "100.000", "hp": "5000.000", "hbd": "250.000"},
                "reputation": "72",
                "followers": 256,
                "following": 128,
                "posts_count": 42,
            },
            activity=formatted_activity,
            trending=trending_posts,
        )
    else:
        # Show landing page for non-authenticated users
        return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login route"""
    # If user is already logged in, redirect to dashboard
    if "username" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        # Handle keychain login
        if request.form.get("login_method") == "keychain":
            username = request.form.get("username")
            signature = request.form.get("signature")
            challenge = request.form.get("challenge")

            # In a real app, you would verify the signature here
            # For demo purposes, we're just accepting it

            # Create or update user in database
            user_id = db.create_or_update_user(username, "keychain")

            if user_id:
                # Create a new session
                session_data = session_manager.create_session(
                    username=username,
                    auth_method="keychain",
                    additional_data={"challenge": challenge, "signature": signature},
                )

                if session_data:
                    # Set Flask session variables
                    session["username"] = username
                    session["auth_method"] = "keychain"
                    session["session_id"] = session_data["session_id"]

                    # Load user preferences from database
                    user_data = db.get_user(username)
                    if user_data:
                        if user_data.get("dark_mode") is not None:
                            session["dark_mode"] = bool(user_data.get("dark_mode"))
                        if user_data.get("theme_color"):
                            session["theme_color"] = user_data.get("theme_color")

                    # Log activity
                    db.log_user_activity(
                        username, "auth", {"action": "login", "method": "keychain"}
                    )

                    flash("Successfully logged in with Hive Keychain!", "success")

                    # Get next URL from query parameter or default to dashboard
                    next_url = request.args.get("next")
                    if (
                        next_url
                        and next_url.startswith("/")
                        and not next_url.startswith("//")
                    ):
                        return redirect(next_url)
                    return redirect(url_for("index"))
                else:
                    flash("Failed to create user session.", "error")
            else:
                flash("Failed to create or update user.", "error")

        # Handle regular username login or demo login
        elif request.form.get("login_method") == "demo" or request.form.get("username"):
            username = request.form.get("username") or "demo"

            # Create or update user
            is_demo = username == "demo"
            user_id = db.create_or_update_user(
                username, "demo" if is_demo else "basic", is_demo=is_demo
            )

            if user_id:
                # Create a new session
                session_data = session_manager.create_session(
                    username=username,
                    auth_method="demo" if is_demo else "basic",
                    additional_data={"is_demo": is_demo},
                )

                if session_data:
                    # Set Flask session variables
                    session["username"] = username
                    session["auth_method"] = "demo" if is_demo else "basic"
                    session["session_id"] = session_data["session_id"]

                    # Load user preferences from database
                    user_data = db.get_user(username)
                    if user_data:
                        if user_data.get("dark_mode") is not None:
                            session["dark_mode"] = bool(user_data.get("dark_mode"))
                        if user_data.get("theme_color"):
                            session["theme_color"] = user_data.get("theme_color")

                    # Log activity
                    db.log_user_activity(
                        username,
                        "auth",
                        {"action": "login", "method": "demo" if is_demo else "basic"},
                    )

                    message = (
                        "You are now using a demo account. Limited functionality available."
                        if is_demo
                        else f"Welcome back, {username}!"
                    )
                    flash(message, "info")

                    # Get next URL from query parameter or default to dashboard
                    next_url = request.args.get("next")
                    if (
                        next_url
                        and next_url.startswith("/")
                        and not next_url.startswith("//")
                    ):
                        return redirect(next_url)
                    return redirect(url_for("index"))
                else:
                    flash("Failed to create user session.", "error")
            else:
                flash("Failed to create or update user.", "error")

    return render_template("login.html")


@app.route("/login-hiveauth", methods=["POST"])
def login_hiveauth():
    """Handle HiveAuth login submission"""
    username = request.form.get("username")
    auth_token = request.form.get("auth_token")
    uuid = request.form.get("uuid")

    if not all([username, auth_token, uuid]):
        flash("Missing required authentication parameters", "danger")
        return redirect(url_for("login"))

    # In a real implementation, you would verify with HiveAuth API
    # For example:
    # verification = verify_hiveauth(username, auth_token, uuid)
    # if not verification.success:
    #     flash("HiveAuth verification failed: " + verification.message, "danger")
    #     return redirect(url_for("login"))

    # For this demo, we'll accept the authentication
    user_id = db.create_or_update_user(username, "hiveauth")

    if user_id:
        # Create a new session
        session_data = session_manager.create_session(
            username=username,
            auth_method="hiveauth",
            additional_data={"token": auth_token, "uuid": uuid},
        )

        if session_data:
            # Set session data
            session["username"] = username
            session["auth_method"] = "hiveauth"
            session["session_id"] = session_data["session_id"]

            # Load user preferences
            user_data = db.get_user(username)
            if user_data:
                if user_data.get("dark_mode") is not None:
                    session["dark_mode"] = bool(user_data.get("dark_mode"))
                if user_data.get("theme_color") is not None:
                    session["theme_color"] = user_data.get("theme_color")
                if (
                    user_data.get("custom_color") is not None
                    and user_data.get("theme_color") == "custom"
                ):
                    session["custom_color"] = user_data.get("custom_color")
                    session["custom_color_light"] = user_data.get("custom_color_light")
                    session["custom_color_dark"] = user_data.get("custom_color_dark")

            # Log activity
            db.log_user_activity(
                username, "auth", {"action": "login", "method": "hiveauth"}
            )

            flash(f"Welcome, {username}! Authenticated with HiveAuth", "success")

            # Get next URL from query parameter or default to dashboard
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("index"))
        else:
            flash("Failed to create user session.", "error")
    else:
        flash("Failed to create or update user.", "error")

    return redirect(url_for("login"))


@app.route("/api/check-hiveauth", methods=["GET"])
def check_hiveauth():
    """API endpoint to check HiveAuth status"""
    username = request.args.get("username")
    token = request.args.get("auth_token") or request.args.get("token")
    uuid = request.args.get("uuid")

    if not all([username, token, uuid]):
        return jsonify({"error": "Missing required parameters"}), 400

    # In a real app, you would check with the HiveAuth service
    # For demo purposes, we'll simulate authentication success
    return jsonify({"authenticated": True, "username": username})


@app.route("/logout")
def logout():
    """Logout route"""
    if "username" in session:
        # Log the logout action
        db.log_user_activity(session["username"], "auth", {"action": "logout"})

        # Delete the session if we have a session_id
        if "session_id" in session:
            session_manager.delete_session(session["session_id"])

    # Clear the Flask session
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/posts")
def posts():
    """Posts page"""
    # If user is logged in, log this activity
    if "username" in session:
        db.log_user_activity(session["username"], "page_view", {"page": "posts"})

    # In a real app, fetch posts from Hive API
    # For demo, use hardcoded data
    return render_template("posts.html", posts=DEMO_POSTS)


@app.route("/post/<author>/<permlink>")
def view_post(author, permlink):
    """View a specific post"""
    # Check if post is cached in database
    cached_post = db.get_cached_post(author, permlink)

    if cached_post:
        post = cached_post
    else:
        # In a real app, fetch post from Hive API
        # For demo, find in demo posts or return 404
        post = None
        for p in DEMO_POSTS:
            if p["author"] == author and p["permlink"] == permlink:
                post = p
                break

        if post:
            # Cache the post
            db.cache_post(author, permlink, post)

    if not post:
        flash("Post not found.", "error")
        return redirect(url_for("posts"))

    # If user is logged in, log this activity
    if "username" in session:
        db.log_user_activity(
            session["username"],
            "post_view",
            {"author": author, "permlink": permlink, "title": post.get("title")},
        )

    return render_template("post_detail.html", post=post)


@app.route("/profile/<username>")
def profile(username):
    """User profile page"""
    # Check if user exists in database
    user_data = db.get_user(username)

    if not user_data and username != "demo":
        flash("User not found.", "error")
        return redirect(url_for("index"))

    # If viewing own profile, log the activity
    if "username" in session and session["username"] == username:
        db.log_user_activity(
            session["username"], "profile_view", {"username": username}
        )

    # For demo, use static data
    # In a real app, you would fetch this from Hive API
    posts = DEMO_POSTS if username == "demo" else []

    # Use profile data from database if available
    profile_details = {}
    if user_data:
        profile = user_data.get("profile", {})
        profile_details = {
            "username": username,
            "name": profile.get("name", username),
            "about": profile.get("about", "No bio yet"),
            "location": profile.get("location", ""),
            "website": profile.get("website", ""),
            "followers": 256,  # This would come from Hive API in a real app
            "following": 128,  # This would come from Hive API in a real app
            "post_count": len(posts),
            "reputation": "72",  # This would come from Hive API in a real app
            "join_date": user_data.get("created_at", "2023-01-01"),
        }
    else:
        # Default data for demo user
        profile_details = {
            "username": username,
            "name": "Demo User",
            "about": "This is a demo account for testing HiveBuzz features.",
            "location": "Blockchain",
            "website": "https://hive.blog",
            "followers": 256,
            "following": 128,
            "post_count": len(posts),
            "reputation": "72",
            "join_date": "2023-01-01",
        }

    return render_template(
        "profile.html", profile_user=username, user_data=profile_details, posts=posts
    )


@app.route("/create", methods=["GET", "POST"])
@login_required
def create_post():
    """Create post page"""
    if request.method == "POST":
        # Get form data
        title = request.form.get("title")
        body = request.form.get("body")
        tags_str = request.form.get("tags")

        if not title or not body:
            flash("Title and content are required", "warning")
            return redirect(url_for("create_post"))

        # Parse tags from comma-separated string
        tags = (
            [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            if tags_str
            else []
        )

        # In a real app, you would submit this post to the Hive blockchain
        # For demo, just show a success message

        # Log activity
        db.log_user_activity(
            session["username"], "post_create", {"title": title, "tags": tags}
        )

        flash("Your post has been submitted!", "success")
        return redirect(url_for("posts"))

    # Log page view
    db.log_user_activity(session["username"], "page_view", {"page": "create_post"})

    return render_template("create_post.html")


@app.route("/api/get_account_info/<username>")
def get_account_info(username):
    """API to get account information"""
    # Check if user exists in database
    user_data = db.get_user(username)

    if user_data:
        profile = user_data.get("profile", {})

        # Return user information
        return jsonify(
            {
                "username": username,
                "name": profile.get("name", username),
                "about": profile.get("about", ""),
                "profile_image": profile.get(
                    "profile_image", f"https://images.hive.blog/u/{username}/avatar"
                ),
                "is_demo": bool(user_data.get("is_demo", False)),
            }
        )
    else:
        # User not found
        return jsonify({"error": "User not found"}), 404


@app.route("/trending")
def trending():
    """Trending posts page"""
    # If user is logged in, log this activity
    if "username" in session:
        db.log_user_activity(session["username"], "page_view", {"page": "trending"})

    # In a real app, fetch trending posts from Hive API
    # For demo, use hardcoded data with random order to simulate different results
    random_posts = DEMO_POSTS.copy()
    random.shuffle(random_posts)

    return render_template("trending.html", posts=random_posts)


@app.route("/api/user/preferences", methods=["GET", "POST"])  # type: ignore
def user_preferences():
    """API endpoint for user preferences"""
    if "username" not in session:
        return jsonify({"error": "Authentication required"}), 401

    if request.method == "GET":
        # Get user preferences from database
        user_data = db.get_user(session["username"])
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        preferences = {
            "theme_color": user_data.get("theme_color", "blue"),
            "dark_mode": bool(user_data.get("dark_mode", False)),
            "display_nsfw": bool(user_data.get("display_nsfw", False)),
            "language": user_data.get("language", "en"),
        }

        # Add additional settings if present
        if "additional_settings" in user_data:
            preferences.update(user_data["additional_settings"])

        return jsonify(preferences)

    elif request.method == "POST":
        # Update preferences
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        preferences = request.get_json()
        if not preferences:
            return jsonify({"error": "No preferences provided"}), 400

        if db.save_user_preferences(session["username"], preferences):
            # Update session for immediate effect
            if "dark_mode" in preferences:
                session["dark_mode"] = bool(preferences["dark_mode"])
            if "theme_color" in preferences:
                session["theme_color"] = preferences["theme_color"]

            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to save preferences"}), 500


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page"""
    if request.method == "POST":
        # Handle settings update
        theme_color = request.form.get("theme_color")
        dark_mode = request.form.get("dark_mode") == "on"
        display_nsfw = request.form.get("display_nsfw") == "on"
        language = request.form.get("language")

        # Get custom color if theme is set to custom
        custom_color = None
        if theme_color == "custom":
            custom_color = request.form.get("custom_color")

            # Generate lighter and darker variants for the custom color
            if custom_color:
                try:
                    # Convert hex to RGB
                    r = int(custom_color[1:3], 16)
                    g = int(custom_color[3:5], 16)
                    b = int(custom_color[5:7], 16)

                    # Generate lighter variant (20% lighter)
                    lighter_r = min(255, int(r + (255 - r) * 0.2))
                    lighter_g = min(255, int(g + (255 - g) * 0.2))
                    lighter_b = min(255, int(b + (255 - b) * 0.2))
                    custom_color_light = (
                        f"#{lighter_r:02x}{lighter_g:02x}{lighter_b:02x}"
                    )

                    # Generate darker variant (20% darker)
                    darker_r = max(0, int(r * 0.8))
                    darker_g = max(0, int(g * 0.8))
                    darker_b = max(0, int(b * 0.8))
                    custom_color_dark = f"#{darker_r:02x}{darker_g:02x}{darker_b:02x}"
                except Exception as e:
                    logger.error(f"Error processing custom color: {e}")
                    custom_color_light = "#9589f6"  # Default light variant
                    custom_color_dark = "#4824eb"  # Default dark variant
            else:
                custom_color = "#7367f0"  # Default custom color
                custom_color_light = "#9589f6"
                custom_color_dark = "#4824eb"

        # Update preferences in database
        preferences = {
            "theme_color": theme_color,
            "dark_mode": 1 if dark_mode else 0,  # SQLite uses integers for booleans
            "display_nsfw": 1 if display_nsfw else 0,
            "language": language,
        }

        # Add custom color if present
        if custom_color:
            preferences["custom_color"] = custom_color
            preferences["custom_color_light"] = custom_color_light
            preferences["custom_color_dark"] = custom_color_dark

        if db.save_user_preferences(session["username"], preferences):
            # Update session for immediate effect
            session["dark_mode"] = dark_mode
            session["theme_color"] = theme_color
            if custom_color:
                session["custom_color"] = custom_color
                session["custom_color_light"] = custom_color_light
                session["custom_color_dark"] = custom_color_dark

            flash("Settings updated successfully!", "success")
        else:
            flash("Failed to save settings.", "error")

        return redirect(url_for("settings"))

    # Get current user preferences
    user_data = db.get_user(session["username"]) or {}

    # Create preferences dictionary to pass to the template
    preferences = {
        "theme_color": user_data.get("theme_color", "blue"),
        "dark_mode": bool(user_data.get("dark_mode", False)),
        "display_nsfw": bool(user_data.get("display_nsfw", False)),
        "language": user_data.get("language", "en"),
        "custom_color": user_data.get("custom_color", "#7367f0"),
        "custom_color_light": user_data.get("custom_color_light", "#9589f6"),
        "custom_color_dark": user_data.get("custom_color_dark", "#4824eb"),
        # Add other preference fields if needed by the template
        "notify_comments": bool(user_data.get("notify_comments", False)),
        "notify_upvotes": bool(user_data.get("notify_upvotes", False)),
        "notify_follows": bool(user_data.get("notify_follows", False)),
        "show_voting_value": bool(user_data.get("show_voting_value", True)),
        "show_profile": bool(user_data.get("show_profile", True)),
    }

    return render_template(
        "settings.html",
        user=user_data,
        preferences=preferences,
    )


@app.route("/wallet")
@login_required
def wallet():
    """User wallet page"""
    # Log this activity
    db.log_user_activity(session["username"], "page_view", {"page": "wallet"})

    # In a real app, fetch wallet data from Hive API
    # For demo, use hardcoded data
    return render_template(
        "wallet.html",
        wallet={
            "username": session["username"],
            "hive_balance": "100.000 HIVE",
            "hbd_balance": "250.000 HBD",
            "hive_power": "5000.000 HP",
            "savings_hive": "50.000 HIVE",
            "savings_hbd": "100.000 HBD",
            "vesting_shares": "10000.000000 VESTS",
            "delegated_vesting_shares": "0.000000 VESTS",
            "received_vesting_shares": "0.000000 VESTS",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        transactions=[
            {
                "type": "transfer",
                "from": "user1",
                "to": session["username"],
                "amount": "10.000 HIVE",
                "memo": "Payment for services",
                "timestamp": "2023-06-01 14:30:25",
            },
            {
                "type": "transfer",
                "from": session["username"],
                "to": "user2",
                "amount": "5.000 HIVE",
                "memo": "Donation",
                "timestamp": "2023-05-28 09:15:10",
            },
            {
                "type": "claim_reward_balance",
                "reward_hive": "1.000 HIVE",
                "reward_hbd": "0.500 HBD",
                "reward_vests": "100.000000 VESTS",
                "timestamp": "2023-05-27 00:00:00",
            },
        ],
    )


@app.route("/hivesigner/callback")
def hivesigner_callback():
    """HiveSigner callback endpoint"""
    # Get the authorization code from the query parameters
    code = request.args.get("code")
    state = request.args.get("state", "")

    if not code:
        flash("Authorization failed - no code provided", "error")
        return redirect(url_for("login"))

    # Get callback URL for token exchange
    redirect_uri = url_for("hivesigner_callback", _external=True)

    # Log the callback parameters for debugging
    logger.info(
        f"HiveSigner callback received: code={code[:10]}..., state={state}, redirect_uri={redirect_uri}"
    )

    # Get HiveSigner client
    hivesigner = get_hivesigner_client()
    if not hivesigner:
        flash("HiveSigner client not initialized", "error")
        return redirect(url_for("login"))

    # Exchange code for token
    success, result = hivesigner.get_token(code, redirect_uri)

    if not success:
        error_message = result.get("error", "Unknown error")
        details = result.get("details", "No additional details")
        logger.error(f"HiveSigner authentication failed: {error_message} - {details}")

        # Provide a more user-friendly error message
        flash(
            f"Authentication failed. Please try again or use another login method.",
            "error",
        )
        return redirect(url_for("login"))

    # Implement fallback option for unusual response formats
    if isinstance(result, dict) and "access_token" not in result:
        if "username" in result:
            # Direct user info without token - unusual but we can work with it
            username = result["username"]
            access_token = "direct_user_info"  # Placeholder
        else:
            # No recognizable data - fail gracefully
            logger.error(f"Unexpected HiveSigner response format: {result}")
            flash(
                "Received unexpected response from HiveSigner. Please try again.",
                "error",
            )
            return redirect(url_for("login"))
    else:
        # Get access token from regular response
        access_token = result.get("access_token")

        if not access_token:
            logger.error(f"No access token found in response: {result}")
            flash("Invalid authentication response", "error")
            return redirect(url_for("login"))

        # Verify token and get user info
        try:
            success, user_data = hivesigner.verify_token(access_token)

            if not success or "user" not in user_data:
                logger.error(
                    f"Failed to verify token: {user_data.get('error', 'Unknown error')}"
                )
                flash("Failed to verify authentication", "error")
                return redirect(url_for("login"))

            username = user_data["user"]
        except Exception as e:
            logger.exception("Exception during token verification")
            flash("An error occurred during authentication verification", "error")
            return redirect(url_for("login"))

    if not username:
        flash("No username returned from HiveSigner", "error")
        return redirect(url_for("login"))

    # Create or update user in database
    try:
        user_id = db.create_or_update_user(username, "hivesigner")

        if not user_id:
            logger.error(f"Failed to create user in database: {username}")
            flash("Failed to create user account. Please try again.", "error")
            return redirect(url_for("login"))

        # Create a new session
        session_data = session_manager.create_session(
            username=username,
            auth_method="hivesigner",
            additional_data={
                "code": code,
                "state": state,
                "access_token": access_token,
            },
        )

        if not session_data:
            logger.error(f"Failed to create session for user: {username}")
            flash("Failed to create user session.", "error")
            return redirect(url_for("login"))

        # Set session data
        session["username"] = username
        session["auth_method"] = "hivesigner"
        session["session_id"] = session_data["session_id"]
        session["hivesigner_token"] = access_token

        # Load user preferences
        user_data = db.get_user(username)
        if user_data:
            if user_data.get("dark_mode") is not None:
                session["dark_mode"] = bool(user_data.get("dark_mode"))
            if user_data.get("theme_color"):
                session["theme_color"] = user_data.get("theme_color")
            if (
                user_data.get("custom_color")
                and user_data.get("theme_color") == "custom"
            ):
                session["custom_color"] = user_data.get("custom_color")
                session["custom_color_light"] = user_data.get("custom_color_light")
                session["custom_color_dark"] = user_data.get("custom_color_dark")

        # Log activity
        db.log_user_activity(
            username, "auth", {"action": "login", "method": "hivesigner"}
        )

        flash("Successfully logged in with HiveSigner!", "success")
        return redirect(url_for("index"))

    except Exception as e:
        logger.exception(f"Unexpected error during HiveSigner login process: {e}")
        flash("An unexpected error occurred. Please try again.", "error")

    return redirect(url_for("login"))


# Update Flask app initialization to include blueprint for static files
static_bp = Blueprint(
    "static", __name__, static_folder="static", static_url_path="/static"
)
app.register_blueprint(static_bp)


# Add a context processor to inject information about current page to templates
@app.context_processor
def inject_template_vars():
    return {
        "page": request.endpoint,
        "path": request.path,
        "dark_mode": session.get("dark_mode", False),
        "theme_color": session.get("theme_color", "blue"),
    }


# Add context processor to make configuration available to templates
@app.context_processor
def inject_config():
    """Make selected configuration variables available to templates"""
    return {
        "config": {
            "HIVESIGNER_APP_NAME": app.config["HIVESIGNER_APP_NAME"],
            "HIVESIGNER_REDIRECT_URI": app.config["HIVESIGNER_REDIRECT_URI"],
            "HIVESIGNER_APP_HOST": app.config["HIVESIGNER_APP_HOST"],
            "APP_URL": app.config["APP_URL"],
            "DEBUG": app.config["DEBUG"],
        }
    }


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template("error.html", error=str(e)), 500


@app.route("/maintenance/clear-expired-sessions")
def clear_expired_sessions():
    """Maintenance endpoint to clear expired sessions"""
    # This should be protected in production
    if request.remote_addr != "127.0.0.1" and not app.debug:
        return jsonify({"error": "Unauthorized"}), 403

    count = session_manager.clear_expired_sessions()
    return jsonify({"success": True, "cleared_count": count}), 200


@app.route("/dashboard")
def dashboard():
    """Dashboard redirect - ensures proper navigation"""
    if "username" in session:
        return redirect(url_for("index"))
    else:
        flash("Please log in to access your dashboard", "warning")
        return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
