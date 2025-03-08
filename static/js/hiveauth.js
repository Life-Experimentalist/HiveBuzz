class HiveAuth {
	constructor(options = {}) {
		this.authEndpoint = options.authEndpoint || "https://hiveauth.com/api/";
		this.client = options.client || "hivebuzz";
		this.challenge = options.challenge || this.generateUUID();
		this.key = options.key || this.generateUUID();
		this.ws = null;

		// Add CORS proxy if needed for local development
		this.useProxy = options.useProxy || false;
		this.corsProxy =
			options.corsProxy || "https://cors-anywhere.herokuapp.com/";
	}

	generateUUID() {
		return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
			/[xy]/g,
			function (c) {
				const r = (Math.random() * 16) | 0,
					v = c === "x" ? r : (r & 0x3) | 0x8;
				return v.toString(16);
			}
		);
	}

	async getAuthData() {
		try {
			const url = `${this.authEndpoint}auth_data?client=${this.client}&challenge=${this.challenge}&key=${this.key}`;
			const fetchUrl = this.useProxy ? `${this.corsProxy}${url}` : url;

			console.log("Fetching auth data from:", fetchUrl);

			const response = await fetch(fetchUrl, {
				method: "GET",
				headers: {
					Accept: "application/json",
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				console.error(
					"HTTP error:",
					response.status,
					response.statusText
				);
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Error getting auth data:", error);
			throw error;
		}
	}

	async getToken(username) {
		try {
			const url = `${this.authEndpoint}get_token?username=${username}&client=${this.client}&challenge=${this.challenge}&key=${this.key}`;
			const fetchUrl = this.useProxy ? `${this.corsProxy}${url}` : url;

			console.log("Getting token from:", fetchUrl);

			const response = await fetch(fetchUrl, {
				method: "GET",
				headers: {
					Accept: "application/json",
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Error getting token:", error);
			throw error;
		}
	}

	connectWebSocket(authData, callback) {
		if (this.ws) this.ws.close();

		console.log("Connecting to WebSocket with auth data:", authData);

		this.ws = new WebSocket("wss://hiveauth.com/ws/");

		this.ws.onopen = () => {
			console.log("WebSocket connection opened");
			this.ws.send(
				JSON.stringify({
					cmd: "register",
					uuid: authData.uuid,
					key: this.key,
				})
			);
		};

		this.ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				console.log("WebSocket message received:", data);

				if (data.cmd === "auth_wait") {
					// Waiting for user to approve
					console.log("Waiting for user authentication...");
				} else if (data.cmd === "auth_ack") {
					// Authentication successful
					console.log("Authentication successful!");
					callback(true, data.username, data);
					this.ws.close();
				} else if (data.cmd === "auth_nack") {
					// Authentication failed/rejected
					console.log("Authentication rejected!");
					callback(false, null, data);
					this.ws.close();
				}
			} catch (error) {
				console.error("Error handling WebSocket message:", error);
				callback(false, null, { error: error.message });
			}
		};

		this.ws.onerror = (error) => {
			console.error("WebSocket error:", error);
			callback(false, null, { error: "WebSocket connection failed" });
		};

		this.ws.onclose = () => {
			console.log("WebSocket connection closed");
		};
	}

	// Mock method for testing without actual API calls
	mockAuthentication(username) {
		console.log("Using mock authentication for testing");

		const mockAuthData = {
			uuid: this.generateUUID(),
			login_url:
				"https://hivesigner.com/oauth2/authorize?client_id=test&redirect_uri=https://example.com",
		};

		const mockTokenResponse = {
			token: "mock_token_" + Date.now(),
		};

		setTimeout(() => {
			console.log("Mock authentication successful");
			return {
				authData: mockAuthData,
				tokenResponse: mockTokenResponse,
			};
		}, 1000);
	}
}

// Initialize HiveAuth functionality when document is ready
document.addEventListener("DOMContentLoaded", function () {
	const hiveauthLoginBtn = document.getElementById("hiveauth-login-btn");

	if (hiveauthLoginBtn) {
		hiveauthLoginBtn.addEventListener("click", async function () {
			const username = document.getElementById("hiveauth-username").value;
			if (!username) {
				alert("Please enter your username");
				return;
			}

			const loadingIndicator =
				document.getElementById("hiveauth-loading");
			if (loadingIndicator) loadingIndicator.style.display = "block";

			try {
				// Use useProxy: true for local development to bypass CORS issues
				const hiveAuth = new HiveAuth({
					client: "hivebuzz",
					useProxy: true,
				});

				// Get auth data from HiveAuth service
				let authData;
				try {
					authData = await hiveAuth.getAuthData();
					console.log("Auth data:", authData);
				} catch (error) {
					console.error("Error getting auth data:", error);
					alert(
						"Error connecting to HiveAuth. Please try again later."
					);
					if (loadingIndicator)
						loadingIndicator.style.display = "none";
					return;
				}

				// Show QR code container
				const qrContainer = document.getElementById("qrcode-container");
				if (qrContainer) qrContainer.style.display = "block";

				// Generate QR code
				const qrcodeElement =
					document.getElementById("hiveauth-qrcode");
				if (qrcodeElement) {
					qrcodeElement.innerHTML = "";
					try {
						await QRCode.toCanvas(
							qrcodeElement,
							authData.login_url,
							{
								width: 200,
								margin: 1,
							}
						);
					} catch (error) {
						console.error("Error generating QR code:", error);
						qrcodeElement.innerText =
							"Error generating QR code. Please use the HiveAuth app and enter this code: " +
							authData.uuid;
					}
				}

				// Get token
				let tokenResponse;
				try {
					tokenResponse = await hiveAuth.getToken(username);
					console.log("Token response:", tokenResponse);
				} catch (error) {
					console.error("Error getting token:", error);
					alert(
						"Error getting authentication token. Please try again."
					);
					if (loadingIndicator)
						loadingIndicator.style.display = "none";
					if (qrContainer) qrContainer.style.display = "none";
					return;
				}

				// Connect WebSocket to wait for authentication
				hiveAuth.connectWebSocket(
					authData,
					function (success, authenticatedUser, data) {
						if (loadingIndicator)
							loadingIndicator.style.display = "none";

						if (success && authenticatedUser) {
							// Create hidden form to submit data to server
							const form = document.createElement("form");
							form.method = "POST";
							form.action = "/login-hiveauth";

							const usernameInput =
								document.createElement("input");
							usernameInput.type = "hidden";
							usernameInput.name = "username";
							usernameInput.value = authenticatedUser;

							const tokenInput = document.createElement("input");
							tokenInput.type = "hidden";
							tokenInput.name = "auth_token";
							tokenInput.value = tokenResponse.token;

							const uuidInput = document.createElement("input");
							uuidInput.type = "hidden";
							uuidInput.name = "uuid";
							uuidInput.value = authData.uuid;

							form.appendChild(usernameInput);
							form.appendChild(tokenInput);
							form.appendChild(uuidInput);

							document.body.appendChild(form);
							form.submit();
						} else {
							alert(
								"Authentication failed or was canceled. Please try again."
							);
							if (qrContainer) qrContainer.style.display = "none";
						}
					}
				);
			} catch (error) {
				console.error("HiveAuth error:", error);
				alert("HiveAuth error: " + error.message);
				if (loadingIndicator) loadingIndicator.style.display = "none";
			}
		});
	}
});
