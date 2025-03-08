document.addEventListener("DOMContentLoaded", function () {
	// Function to check if Hive Keychain is installed
	function checkForKeychain() {
		const keychainInstalled = window.hive_keychain || false;
		const keychainNoticeDiv = document.getElementById("keychain-notice");
		const keychainLoginBtn = document.getElementById("keychain-login-btn");

		console.log(
			"Checking for Hive Keychain:",
			keychainInstalled ? "Found" : "Not found"
		);

		if (!keychainInstalled) {
			if (keychainNoticeDiv) {
				keychainNoticeDiv.style.display = "block";
			}
			if (keychainLoginBtn) {
				keychainLoginBtn.disabled = true;
			}
		} else {
			if (keychainNoticeDiv) {
				keychainNoticeDiv.style.display = "none";
			}
			if (keychainLoginBtn) {
				keychainLoginBtn.disabled = false;
			}
		}

		return keychainInstalled;
	}

	// Function to handle Hive Keychain login
	function loginWithKeychain() {
		const username = document.getElementById("keychain-username").value;
		if (!username) {
			alert("Please enter your Hive username");
			return;
		}

		console.log(
			"Attempting to login with Hive Keychain for user:",
			username
		);

		// Generate a random string as challenge for the signature
		const challenge = Math.random().toString(36).substring(2);

		// Request signature from Hive Keychain
		if (window.hive_keychain) {
			window.hive_keychain.requestSignBuffer(
				username,
				`Login to HiveBuzz: ${challenge}`,
				"Posting",
				(response) => {
					console.log("Keychain response:", response);

					if (response.success) {
						// Create a form to submit the data to server
						const form = document.createElement("form");
						form.method = "POST";
						form.action = "/login";

						// Add username
						const usernameInput = document.createElement("input");
						usernameInput.type = "hidden";
						usernameInput.name = "username";
						usernameInput.value = username;

						// Add signature
						const signatureInput = document.createElement("input");
						signatureInput.type = "hidden";
						signatureInput.name = "signature";
						signatureInput.value = response.result;

						// Add challenge
						const challengeInput = document.createElement("input");
						challengeInput.type = "hidden";
						challengeInput.name = "challenge";
						challengeInput.value = challenge;

						// Append inputs to form
						form.appendChild(usernameInput);
						form.appendChild(signatureInput);
						form.appendChild(challengeInput);

						// Append form to body and submit
						document.body.appendChild(form);
						form.submit();
					} else {
						alert(
							`Error: ${
								response.message ||
								"Could not sign with Keychain"
							}`
						);
					}
				}
			);
		} else {
			alert(
				"Hive Keychain not found. Please install the extension first."
			);
		}
	}

	// Check if Keychain exists on page load
	setTimeout(checkForKeychain, 500); // Give a slight delay for Keychain to initialize

	// Set up event listener for the login button
	const keychainLoginBtn = document.getElementById("keychain-login-btn");
	if (keychainLoginBtn) {
		keychainLoginBtn.addEventListener("click", function () {
			if (checkForKeychain()) {
				loginWithKeychain();
			} else {
				alert(
					"Hive Keychain not found. Please install the extension first."
				);
			}
		});
	}
});
