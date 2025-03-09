/**
 * Hive Keychain Helper for HiveBuzz
 * Provides utilities for interacting with the Hive Keychain browser extension
 */

class HiveKeychainHelper {
	/**
	 * Check if Hive Keychain is installed
	 * @returns {boolean} True if Hive Keychain is available
	 */
	static isKeychainInstalled() {
		return window.hive_keychain ? true : false;
	}

	/**
	 * Request a login through Keychain
	 * @param {string} username - Hive username
	 * @param {string} [challenge] - Optional challenge string, generates one if not provided
	 * @returns {Promise} Resolves with signed challenge data, rejects on error
	 */
	static requestLogin(username, challenge = null) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject("Hive Keychain is not installed");
				return;
			}

			if (!username) {
				reject("Username is required");
				return;
			}

			// Generate a random challenge if none provided
			const loginChallenge =
				challenge ||
				`hivebuzz-auth-${Math.random().toString(36).substring(2, 15)}`;

			window.hive_keychain.requestSignBuffer(
				username,
				`Login to HiveBuzz: ${loginChallenge}`,
				"Posting",
				(response) => {
					console.log("Keychain login response:", response);

					if (response.success) {
						resolve({
							username: username,
							signature: response.result,
							challenge: loginChallenge,
						});
					} else {
						reject(response.message || "Authentication failed");
					}
				}
			);
		});
	}

	/**
	 * Request a simple vote/upvote through Keychain
	 * @param {string} username - Voter's username
	 * @param {string} author - Post author
	 * @param {string} permlink - Post permlink
	 * @param {number} weight - Vote weight (10000 = 100%)
	 * @returns {Promise} Resolves on successful vote, rejects on error
	 */
	static requestVote(username, author, permlink, weight = 10000) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject("Hive Keychain is not installed");
				return;
			}

			window.hive_keychain.requestVote(
				username,
				permlink,
				author,
				weight,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(response.message || "Vote failed");
					}
				}
			);
		});
	}

	/**
	 * Request a transfer operation through Keychain
	 * @param {string} username - Sender's username
	 * @param {string} to - Recipient's username
	 * @param {string} amount - Amount with currency (e.g. "1.000 HIVE")
	 * @param {string} memo - Transfer memo
	 * @returns {Promise} Resolves on successful transfer, rejects on error
	 */
	static requestTransfer(username, to, amount, memo = "") {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject("Hive Keychain is not installed");
				return;
			}

			window.hive_keychain.requestTransfer(
				username,
				to,
				amount,
				memo,
				"Active",
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(response.message || "Transfer failed");
					}
				}
			);
		});
	}

	/**
	 * Request a custom JSON operation through Keychain
	 * @param {string} username - Account username
	 * @param {string} id - Custom JSON ID (e.g. "follow")
	 * @param {string} key - Required authority ("Active" or "Posting")
	 * @param {Object} json - JSON data to broadcast
	 * @returns {Promise} Resolves on success, rejects on error
	 */
	static requestCustomJson(username, id, key, json) {
		return new Promise((resolve, reject) => {
			if (!this.isKeychainInstalled()) {
				reject("Hive Keychain is not installed");
				return;
			}

			window.hive_keychain.requestCustomJson(
				username,
				id,
				key,
				JSON.stringify(json),
				`HiveBuzz ${id} operation`,
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(response.message || "Operation failed");
					}
				}
			);
		});
	}

	/**
	 * Check the status of Hive Keychain and update UI elements accordingly
	 * @param {string} statusElementId - ID of element to update with status
	 * @param {string} buttonElementId - ID of button to enable/disable
	 */
	static updateKeychainStatus(
		statusElementId = "keychain-status",
		buttonElementId = "keychain-login-btn"
	) {
		const statusElement = document.getElementById(statusElementId);
		const buttonElement = document.getElementById(buttonElementId);

		if (!statusElement) return;

		setTimeout(() => {
			const keychainInstalled = this.isKeychainInstalled();

			if (keychainInstalled) {
				statusElement.innerHTML =
					'<div class="d-flex align-items-center"><i class="bi bi-check-circle-fill text-success me-2"></i> <span>Hive Keychain detected and ready!</span></div>';
				statusElement.classList.remove("alert-info", "alert-danger");
				statusElement.classList.add("alert-success");
				if (buttonElement) buttonElement.disabled = false;
			} else {
				statusElement.innerHTML =
					'<div class="d-flex align-items-center"><i class="bi bi-x-circle-fill text-danger me-2"></i> <span>Hive Keychain not detected! Please <a href="https://chrome.google.com/webstore/detail/hive-keychain/jcacnejopjdphbnjgfaaobbfafkihpep" target="_blank">install the extension</a> first.</span></div>';
				statusElement.classList.remove("alert-info", "alert-success");
				statusElement.classList.add("alert-danger");
				if (buttonElement) buttonElement.disabled = true;
			}
		}, 800); // Wait a bit for Keychain to initialize
	}
}

// Initialize the helper when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
	// Make the helper available globally
	window.HiveKeychainHelper = HiveKeychainHelper;

	// Check keychain status on pages that have the status indicator
	if (document.getElementById("keychain-status")) {
		HiveKeychainHelper.updateKeychainStatus();
	}
});
