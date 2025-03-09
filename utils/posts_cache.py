"""
Posts Cache Manager for HiveBuzz
Handles caching and background refresh of blockchain posts
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.hive_api import get_hive_api

# Configure logging
logger = logging.getLogger(__name__)

# Default cache settings
DEFAULT_REFRESH_INTERVAL = 300  # 5 minutes in seconds
DEFAULT_CACHE_SIZE = 50  # Number of posts to cache per feed type
STARTUP_PRIORITY_FEEDS = ["trending", "hot"]  # Load these first during startup
DEFAULT_CACHE_DIR = "cache/posts"  # Directory to store persistent cache files
MAX_CACHE_AGE = 3600  # Maximum age of cache files in seconds (1 hour)


class PostsCache:
    """
    Cache manager for blockchain posts
    Maintains separate caches for different feed types and handles background refresh
    """

    def __init__(
        self,
        refresh_interval: int = DEFAULT_REFRESH_INTERVAL,
        cache_dir: str = DEFAULT_CACHE_DIR,
    ):
        """
        Initialize the posts cache

        Args:
            refresh_interval: Time between cache refreshes in seconds
            cache_dir: Directory to store persistent cache files
        """
        self.refresh_interval = refresh_interval
        self.cache_dir = cache_dir
        self.cache: Dict[str, Dict] = {
            "trending": {"posts": [], "last_updated": None, "updating": False},
            "hot": {"posts": [], "last_updated": None, "updating": False},
            "new": {"posts": [], "last_updated": None, "updating": False},
            "promoted": {"posts": [], "last_updated": None, "updating": False},
        }
        self.tag_cache: Dict[str, Dict] = {}  # For caching tag-specific feeds
        self.refresh_thread = None
        self.running = False
        self.initialized = False
        self.event = threading.Event()  # For signaling startup completion
        self._startup_complete = False  # Flag for tracking startup status

        # Ensure cache directory exists
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist"""
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Using cache directory: {os.path.abspath(self.cache_dir)}")

    def _get_cache_file_path(self, feed_type: str, tag: Optional[str] = None) -> str:
        """
        Get the path to the cache file for the specified feed type and tag

        Args:
            feed_type: Type of feed
            tag: Optional tag

        Returns:
            Path to cache file
        """
        if tag:
            filename = f"{feed_type}_{tag}.json"
        else:
            filename = f"{feed_type}.json"
        return os.path.join(self.cache_dir, filename)

    def _load_cache_from_file(self, feed_type: str, tag: Optional[str] = None) -> bool:
        """
        Load cache from file if it exists and is not too old

        Args:
            feed_type: Type of feed
            tag: Optional tag

        Returns:
            True if cache was loaded successfully, False otherwise
        """
        cache_file = self._get_cache_file_path(feed_type, tag)

        try:
            if not os.path.exists(cache_file):
                return False

            # Check file age
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age > MAX_CACHE_AGE:
                logger.info(
                    f"Cache file {cache_file} is too old ({file_age:.1f}s), will refresh"
                )
                return False

            # Load cache from file
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Validate cache data
            if (
                not isinstance(cache_data, dict)
                or "posts" not in cache_data
                or "last_updated" not in cache_data
            ):
                logger.warning(f"Invalid cache file format: {cache_file}")
                return False

            # Update memory cache
            if tag:
                cache_key = f"{feed_type}_{tag}"
                if cache_key not in self.tag_cache:
                    self.tag_cache[cache_key] = {
                        "posts": [],
                        "last_updated": None,
                        "updating": False,
                    }
                self.tag_cache[cache_key]["posts"] = cache_data["posts"]
                self.tag_cache[cache_key]["last_updated"] = datetime.fromisoformat(
                    cache_data["last_updated"]
                )
            else:
                self.cache[feed_type]["posts"] = cache_data["posts"]
                self.cache[feed_type]["last_updated"] = datetime.fromisoformat(
                    cache_data["last_updated"]
                )

            logger.info(
                f"Loaded {len(cache_data['posts'])} posts from cache file {cache_file}"
            )
            return True

        except (json.JSONDecodeError, KeyError, ValueError, IOError) as e:
            logger.warning(f"Error loading cache file {cache_file}: {e}")
            return False

    def _save_cache_to_file(self, feed_type: str, tag: Optional[str] = None) -> None:
        """
        Save cache to file

        Args:
            feed_type: Type of feed
            tag: Optional tag
        """
        cache_file = self._get_cache_file_path(feed_type, tag)

        try:
            # Get cache data
            if tag:
                cache_key = f"{feed_type}_{tag}"
                if (
                    cache_key not in self.tag_cache
                    or not self.tag_cache[cache_key]["posts"]
                ):
                    return
                posts = self.tag_cache[cache_key]["posts"]
                last_updated = self.tag_cache[cache_key]["last_updated"]
            else:
                if feed_type not in self.cache or not self.cache[feed_type]["posts"]:
                    return
                posts = self.cache[feed_type]["posts"]
                last_updated = self.cache[feed_type]["last_updated"]

            # Create cache data dict
            cache_data = {
                "posts": posts,
                "last_updated": (
                    last_updated.isoformat()
                    if last_updated
                    else datetime.now().isoformat()
                ),
                "feed_type": feed_type,
                "tag": tag,
                "count": len(posts),
            }

            # Write to file
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(posts)} posts to cache file {cache_file}")

        except (IOError, TypeError) as e:
            logger.error(f"Error saving cache to file {cache_file}: {e}")

    def start(self) -> None:
        """Start background refresh thread and perform initial (nonblocking) cache load"""
        if not self.running:
            self.running = True

            # First, try to load cached data from files
            logger.info("Loading cached posts from disk")
            for feed_type in self.cache.keys():
                self._load_cache_from_file(feed_type)

            # Instead of blocking on priority feeds, launch them in background
            logger.info("Starting background priority feed refresh")
            threading.Thread(
                target=self._load_priority_feeds,
                name="PriorityFeedsThread",
                daemon=True,
            ).start()

            # Then start continuous background refresh loop
            self.refresh_thread = threading.Thread(
                target=self._background_refresh_loop,
                name="PostsCacheRefreshThread",
                daemon=True,
            )
            self.refresh_thread.start()
            logger.info("Posts cache background refresh started")

    def _load_priority_feeds(self) -> None:
        """Load high priority feeds synchronously during startup"""
        try:
            # First try to load trending posts as these are most commonly needed
            for feed_type in STARTUP_PRIORITY_FEEDS:
                logger.info(f"Loading priority feed: {feed_type}")
                self._refresh_feed(feed_type, None, block=True)

            # Mark as initialized even if we only have some content
            self.initialized = True

        except Exception as e:
            logger.error(f"Error loading priority feeds: {e}")
            # Continue despite errors - we'll retry in background

    def wait_for_initialization(self, timeout: float = 10.0) -> bool:
        """
        Wait for cache initialization to complete

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if initialization completed, False if timed out
        """
        if self.initialized:
            return True

        logger.info(f"Waiting for posts cache initialization (timeout: {timeout}s)")
        return self.event.wait(timeout)

    def stop(self) -> None:
        """Stop the background refresh thread"""
        self.running = False
        if self.refresh_thread and self.refresh_thread.is_alive():
            self.event.set()  # Signal any waiting threads
            self.refresh_thread.join(timeout=2.0)
            logger.info("Posts cache background refresh stopped")

    def get_posts(
        self,
        feed_type: str = "trending",
        tag: Optional[str] = None,
        limit: int = 20,
        timeout: Optional[float] = None,
    ) -> List[Dict]:
        """
        Get posts from the cache for the specified feed type and tag

        Args:
            feed_type: Type of feed (trending, hot, new, promoted)
            tag: Optional tag to filter posts
            limit: Number of posts to return
            timeout: Maximum time to wait for posts in seconds (None for no timeout)

        Returns:
            List of post dictionaries
        """
        # For tag-specific feeds, use the tag cache or fallback to filtering the main feed
        if tag:
            cache_key = f"{feed_type}_{tag}"
            if cache_key in self.tag_cache and self.tag_cache[cache_key]["posts"]:
                posts = self.tag_cache[cache_key]["posts"]
                # If the tag cache is stale (>10 min), trigger a refresh
                if (
                    self.tag_cache[cache_key]["last_updated"] is None
                    or (
                        datetime.now() - self.tag_cache[cache_key]["last_updated"]
                    ).total_seconds()
                    > 600
                ):
                    threading.Thread(
                        name=f"TagRefresh_{feed_type}_{tag}",
                        target=self._refresh_feed,
                        args=(feed_type, tag),
                        daemon=True,
                    ).start()
            else:
                # If no tag cache exists, filter the main feed and create a background fetch
                # for this specific tag
                main_feed = self.cache.get(feed_type, {"posts": []})["posts"]
                posts = [post for post in main_feed if tag in post.get("tags", [])]

                # Start a background fetch for this tag if it's not already being updated
                if (
                    cache_key not in self.tag_cache
                    or not self.tag_cache[cache_key]["updating"]
                ):
                    if cache_key not in self.tag_cache:
                        self.tag_cache[cache_key] = {
                            "posts": [],
                            "last_updated": None,
                            "updating": False,
                        }
                    threading.Thread(
                        name=f"TagRefresh_{feed_type}_{tag}",
                        target=self._refresh_feed,
                        args=(feed_type, tag),
                        daemon=True,
                    ).start()
        else:
            # For main feeds, use the main cache
            posts = self.cache.get(feed_type, {"posts": []})["posts"]

            # Non-blocking wait with timeout if specified
            if timeout is not None and not posts and self.cache[feed_type]["updating"]:
                if feed_type in STARTUP_PRIORITY_FEEDS and not self.initialized:
                    logger.info(
                        f"Priority feed {feed_type} not yet initialized, waiting..."
                    )
                    # For priority feeds during startup, wait briefly for initialization
                    # This ensures we return real data for the most important feeds
                    wait_time = 0
                    max_wait_time = 3  # Max seconds to wait
                    while (
                        not posts
                        and wait_time < max_wait_time
                        and self.cache[feed_type]["updating"]
                    ):
                        time.sleep(0.2)
                        wait_time += 0.2
                        posts = self.cache.get(feed_type, {"posts": []})["posts"]

                # If still no posts, trigger an immediate refresh in background
                if not posts:
                    threading.Thread(
                        name=f"FeedRefresh_{feed_type}",
                        target=self._refresh_feed,
                        args=(feed_type, None),
                        daemon=True,
                    ).start()

        # Return requested number of posts, ensuring we have a list even if empty
        return posts[:limit] if posts else []

    def _background_refresh_loop(self) -> None:
        """Background thread that refreshes the cache periodically"""
        try:
            # Initial refresh of non-priority feeds (priority feeds already loaded)
            self._refresh_remaining_feeds()

            # Mark startup as complete
            self._startup_complete = True
            self.initialized = True
            self.event.set()
            logger.info("Posts cache initialization complete")

            # Continuous refresh loop
            while self.running:
                try:
                    # Sleep for the refresh interval
                    # Use event with timeout instead of time.sleep for better shutdown
                    if self.event.wait(self.refresh_interval):
                        # Event was set - time to exit
                        break

                    # Refresh all feeds
                    self._refresh_all_feeds()

                    # Clean up old tag caches (older than 1 hour)
                    self._cleanup_tag_cache()

                except Exception as e:
                    logger.error(f"Error in posts cache refresh loop: {e}")
                    time.sleep(10)  # Short sleep on error before retrying
        except Exception as e:
            logger.exception(f"Fatal error in posts cache background thread: {e}")
            self.initialized = False  # Mark as failed

    def _refresh_all_feeds(self) -> None:
        """Refresh all main feeds"""
        threads = []
        for feed_type in self.cache.keys():
            thread = threading.Thread(
                name=f"FeedRefresh_{feed_type}",
                target=self._refresh_feed,
                args=(feed_type, None),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        # Wait for all refresh threads to complete with timeout
        for thread in threads:
            thread.join(timeout=30)

    def _refresh_remaining_feeds(self) -> None:
        """Refresh all non-priority feeds after startup"""
        threads = []
        for feed_type in self.cache.keys():
            if feed_type not in STARTUP_PRIORITY_FEEDS:
                thread = threading.Thread(
                    name=f"InitRefresh_{feed_type}",
                    target=self._refresh_feed,
                    args=(feed_type, None),
                    daemon=True,
                )
                thread.start()
                threads.append(thread)

        # Wait for all refresh threads to complete with timeout
        for thread in threads:
            thread.join(timeout=30)

    def _refresh_feed(
        self, feed_type: str, tag: Optional[str] = None, block: bool = False
    ) -> None:
        """
        Refresh a specific feed in the cache

        Args:
            feed_type: Type of feed to refresh
            tag: Optional tag to filter posts
            block: Whether to block until refresh completes (used during startup)
        """
        # Get the appropriate cache (main feed or tag-specific)
        cache_key = f"{feed_type}_{tag}" if tag else feed_type
        cache_dict = (
            self.tag_cache.get(cache_key, {}) if tag else self.cache.get(feed_type, {})
        )

        # Skip if already being updated (unless blocking)
        if cache_dict.get("updating", False) and not block:
            return

        if tag:
            if cache_key not in self.tag_cache:
                self.tag_cache[cache_key] = {
                    "posts": [],
                    "last_updated": None,
                    "updating": False,
                }
            cache_dict = self.tag_cache[cache_key]

        # Mark as updating
        cache_dict["updating"] = True
        start_time = time.time()

        try:
            # Get API client
            hive_api_client = get_hive_api()

            # Fetch posts based on feed type
            if feed_type == "trending":
                posts = hive_api_client.get_trending_posts(
                    limit=DEFAULT_CACHE_SIZE, tag=tag
                )
            elif feed_type == "hot":
                # We're using trending but would ideally use a hot posts endpoint
                posts = hive_api_client.get_trending_posts(
                    limit=DEFAULT_CACHE_SIZE, tag=tag
                )
            elif feed_type == "new":
                # We're using trending but would ideally use a created/new posts endpoint
                posts = hive_api_client.get_trending_posts(
                    limit=DEFAULT_CACHE_SIZE, tag=tag
                )
                # Sort by creation date (newest first) to simulate 'created/new'
                posts.sort(key=lambda post: post.get("created", ""), reverse=True)
            elif feed_type == "promoted":
                # We're using trending but would ideally use a promoted posts endpoint
                posts = hive_api_client.get_trending_posts(
                    limit=DEFAULT_CACHE_SIZE, tag=tag
                )
            else:
                posts = []

            # Filter out posts without titles (likely deleted or invalid)
            posts = [post for post in posts if post.get("title")]

            # Update the cache if we got valid posts
            if posts:
                if tag:
                    self.tag_cache[cache_key]["posts"] = posts
                    self.tag_cache[cache_key]["last_updated"] = datetime.now()
                    # Save tag-specific cache to file
                    self._save_cache_to_file(feed_type, tag)
                else:
                    self.cache[feed_type]["posts"] = posts
                    self.cache[feed_type]["last_updated"] = datetime.now()
                    # Save main feed cache to file
                    self._save_cache_to_file(feed_type)

                duration = time.time() - start_time
                logger.info(
                    f"Updated {cache_key} posts cache with {len(posts)} posts in {duration:.2f}s"
                )
            else:
                logger.warning(
                    f"No posts returned for {cache_key}, keeping existing cache"
                )

        except Exception as e:
            logger.error(f"Error refreshing {cache_key} posts: {e}")
        finally:
            # Mark as no longer updating
            if tag:
                self.tag_cache[cache_key]["updating"] = False
            else:
                self.cache[feed_type]["updating"] = False

    def _cleanup_tag_cache(self) -> None:
        """Remove old tag caches to prevent memory bloat"""
        now = datetime.now()
        keys_to_remove = []

        for key, cache_data in self.tag_cache.items():
            # Remove entries that haven't been updated in over an hour
            if (
                cache_data["last_updated"]
                and (now - cache_data["last_updated"]).total_seconds() > 3600
            ):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.tag_cache[key]

        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} stale tag caches")

    def is_cache_fresh(self, feed_type: str, tag: Optional[str] = None) -> bool:
        """
        Check if the specified cache is fresh (less than refresh_interval old)

        Args:
            feed_type: Type of feed
            tag: Optional tag

        Returns:
            True if cache is fresh, False otherwise
        """
        if tag:
            cache_key = f"{feed_type}_{tag}"
            if cache_key not in self.tag_cache:
                return False
            last_updated = self.tag_cache[cache_key]["last_updated"]
        else:
            if feed_type not in self.cache:
                return False
            last_updated = self.cache[feed_type]["last_updated"]

        if not last_updated:
            return False

        # Check if cache is older than refresh interval
        return (datetime.now() - last_updated).total_seconds() < self.refresh_interval

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get status information about the cache

        Returns:
            Dictionary with cache status information
        """
        status = {
            "initialized": self.initialized,
            "startup_complete": self._startup_complete,
            "running": self.running,
            "feeds": {},
        }

        # Add info for each feed
        for feed_type, feed_data in self.cache.items():
            posts_count = len(feed_data["posts"])
            last_updated = feed_data["last_updated"]
            status["feeds"][feed_type] = {
                "post_count": posts_count,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "has_data": posts_count > 0,
            }

        # Add tag cache stats
        status["tag_cache_count"] = len(self.tag_cache)

        return status

    def is_feed_initializing(self, feed_type: str) -> bool:
        """
        Check if a specific feed is currently being initialized

        Args:
            feed_type: Type of feed to check

        Returns:
            True if feed is currently being updated, False otherwise
        """
        if feed_type not in self.cache:
            return False
        return self.cache[feed_type]["updating"]

    def is_feed_ready(self, feed_type: str) -> bool:
        """
        Check if a feed is ready for use (has posts and is initialized)

        Args:
            feed_type: Type of feed to check

        Returns:
            True if feed has data and is not initializing, False otherwise
        """
        if feed_type not in self.cache:
            return False

        has_posts = len(self.cache[feed_type]["posts"]) > 0
        not_updating = not self.cache[feed_type]["updating"]

        return has_posts and not_updating

    def clear_cache_files(self, older_than: int = 0) -> int:
        """
        Clear cache files that are older than the specified age

        Args:
            older_than: Maximum age of cache files in seconds (0 to clear all)

        Returns:
            Number of files deleted
        """
        deleted_count = 0
        now = time.time()

        try:
            # List all cache files
            cache_files = [
                os.path.join(self.cache_dir, f)
                for f in os.listdir(self.cache_dir)
                if f.endswith(".json")
                and os.path.isfile(os.path.join(self.cache_dir, f))
            ]

            # Delete files older than specified age
            for file_path in cache_files:
                file_age = now - os.path.getmtime(file_path)
                if older_than == 0 or file_age > older_than:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted cache file: {file_path}")

        except Exception as e:
            logger.error(f"Error clearing cache files: {e}")

        logger.info(f"Cleared {deleted_count} cache files")
        return deleted_count


# Create a global instance for app-wide use
_posts_cache_instance = None


def init_posts_cache(refresh_interval: int = DEFAULT_REFRESH_INTERVAL) -> PostsCache:
    """
    Initialize the global PostsCache instance

    Args:
        refresh_interval: Time between cache refreshes in seconds

    Returns:
        PostsCache instance
    """
    global _posts_cache_instance
    if _posts_cache_instance is None:
        _posts_cache_instance = PostsCache(refresh_interval=refresh_interval)
        _posts_cache_instance.start()
    return _posts_cache_instance


def get_posts_cache() -> PostsCache:
    """
    Get the global PostsCache instance, initializing it if necessary

    Returns:
        PostsCache instance
    """
    global _posts_cache_instance
    if _posts_cache_instance is None:
        _posts_cache_instance = PostsCache()
        _posts_cache_instance.start()
    return _posts_cache_instance
