/**
 * Posts functionality for HiveBuzz
 * Handles post interactions, voting, and infinite scrolling
 */

class PostsManager {
	constructor() {
		this.page = 1;
		this.isLoading = false;
		this.hasMorePosts = true;
		this.postsContainer = document.getElementById("posts-container");
		this.loadingIndicator = document.getElementById("loading-posts");
		this.refreshBtn = document.getElementById("refreshBtn");
		this.voteButtons = document.querySelectorAll(".vote-btn");

		// Initialize components
		this.initRefreshButton();
		this.initVoteButtons();
		this.initInfiniteScroll();
	}

	/**
	 * Initialize refresh button
	 */
	initRefreshButton() {
		if (this.refreshBtn) {
			this.refreshBtn.addEventListener("click", () => {
				// Show loading spinner on the button
				const originalHtml = this.refreshBtn.innerHTML;
				this.refreshBtn.innerHTML =
					'<span class="spinner-border spinner-border-sm me-2" role="status"></span> Loading...';
				this.refreshBtn.disabled = true;

				// Reload the page
				window.location.reload();
			});
		}
	}

	/**
	 * Initialize vote buttons for all posts
	 */
	initVoteButtons() {
		this.voteButtons.forEach((btn) => {
			btn.addEventListener("click", async (event) => {
				event.preventDefault();

				const author = btn.dataset.author;
				const permlink = btn.dataset.permlink;
				const username = btn.dataset.username;

				// Check if Hive Keychain is available
				if (
					!HiveKeychainHelper ||
					!HiveKeychainHelper.isKeychainInstalled()
				) {
					this.showNotification(
						"Hive Keychain is required for voting",
						"warning"
					);
					return;
				}

				await this.castVote(btn, username, author, permlink);
			});
		});
	}

	/**
	 * Cast a vote on a post using Hive Keychain
	 *
	 * @param {HTMLElement} button - The vote button element
	 * @param {string} username - Current user's username
	 * @param {string} author - Post author
	 * @param {string} permlink - Post permlink
	 */
	async castVote(button, username, author, permlink) {
		// Default to 100% upvote
		const weight = 10000;

		// Show loading state
		button.disabled = true;
		const originalHtml = button.innerHTML;
		button.innerHTML =
			'<span class="spinner-border spinner-border-sm" role="status"></span>';

		try {
			// Request vote via Hive Keychain
			const response = await HiveKeychainHelper.requestVote(
				username,
				author,
				permlink,
				weight
			);

			if (response.success) {
				// Update vote count and style
				const countElement = button.querySelector(".vote-count");
				if (countElement) {
					countElement.textContent =
						parseInt(countElement.textContent || "0") + 1;
				}

				button.classList.add("active");
				this.showNotification("Vote successful!", "success");
			} else {
				// Show error message
				this.showNotification(
					"Vote failed: " + (response.message || "Unknown error"),
					"danger"
				);
			}
		} catch (error) {
			this.showNotification("Error: " + error, "danger");
		} finally {
			// Restore button state
			button.innerHTML = originalHtml;
			button.disabled = false;
		}
	}

	/**
	 * Initialize infinite scrolling
	 */
	initInfiniteScroll() {
		// Only setup if we have the container
		if (!this.postsContainer) return;

		// Set up intersection observer for infinite scrolling
		const observer = new IntersectionObserver((entries) => {
			if (
				entries[0].isIntersecting &&
				!this.isLoading &&
				this.hasMorePosts
			) {
				this.loadMorePosts();
			}
		});

		// Observe the loading indicator if it exists
		if (this.loadingIndicator) {
			observer.observe(this.loadingIndicator);
		}
	}

	/**
	 * Load more posts when scrolling
	 */
	async loadMorePosts() {
		this.isLoading = true;

		// Show loading indicator
		if (this.loadingIndicator) {
			this.loadingIndicator.classList.remove("d-none");
		}

		try {
			const feedType = document.body.dataset.feedType || "trending";
			const tag = document.body.dataset.tag || "";

			// Increment page number
			this.page++;

			// Make AJAX request to load more posts
			const response = await fetch(
				`/api/posts?feed=${feedType}&tag=${tag}&page=${this.page}`
			);

			if (!response.ok) {
				throw new Error(
					`Error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();

			if (Array.isArray(data.posts) && data.posts.length > 0) {
				// Append new posts to container
				data.posts.forEach((post) => {
					const postElement = this.createPostElement(post);
					this.postsContainer.appendChild(postElement);
				});

				// Initialize vote buttons on new posts
				const newVoteButtons = this.postsContainer.querySelectorAll(
					".vote-btn:not(.initialized)"
				);
				newVoteButtons.forEach((btn) => {
					btn.classList.add("initialized");
					btn.addEventListener("click", async (event) => {
						event.preventDefault();
						const author = btn.dataset.author;
						const permlink = btn.dataset.permlink;
						const username = btn.dataset.username;
						await this.castVote(btn, username, author, permlink);
					});
				});
			} else {
				// No more posts
				this.hasMorePosts = false;
				if (this.loadingIndicator) {
					this.loadingIndicator.innerHTML =
						"<p>No more posts to load</p>";
				}
			}
		} catch (error) {
			console.error("Error loading more posts:", error);
			this.showNotification("Failed to load more posts", "danger");
		} finally {
			this.isLoading = false;

			// Hide loading indicator if no more posts
			if (!this.hasMorePosts && this.loadingIndicator) {
				setTimeout(() => {
					this.loadingIndicator.classList.add("d-none");
				}, 1000);
			}
		}
	}

	/**
	 * Create a post element from post data
	 *
	 * @param {Object} post - Post data
	 * @returns {HTMLElement} - Post element
	 */
	createPostElement(post) {
		// This is a simplified version, you would need to implement this based
		// on your actual post card HTML structure
		const col = document.createElement("div");
		col.className = "col";
		col.innerHTML = `
            <div class="card h-100 post-card">
                <!-- Post content would go here -->
                <div class="card-body">
                    <h5 class="card-title">${post.title}</h5>
                    <p>by @${post.author}</p>
                </div>
            </div>
        `;
		return col;
	}

	/**
	 * Show notification toast
	 *
	 * @param {string} message - Notification message
	 * @param {string} type - Notification type (success, danger, warning, info)
	 */
	showNotification(message, type = "info") {
		const toast = document.createElement("div");
		toast.className = "position-fixed bottom-0 end-0 p-3";
		toast.style.zIndex = "11";
		toast.innerHTML = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-${
							type === "success"
								? "check-circle"
								: type === "danger"
								? "exclamation-circle"
								: "info-circle"
						} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
		document.body.appendChild(toast);

		// Initialize and show the toast
		const toastEl = new bootstrap.Toast(toast.querySelector(".toast"));
		toastEl.show();

		// Remove toast element after it hides
		toast.addEventListener("hidden.bs.toast", () => {
			document.body.removeChild(toast);
		});
	}
}

// Initialize the Posts Manager when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
	const postsManager = new PostsManager();

	// Make it globally accessible for debugging
	window.postsManager = postsManager;
});
