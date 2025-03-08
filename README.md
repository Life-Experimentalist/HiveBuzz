# HiveBuzz

## Overview
HiveBuzz is a decentralized social media application built on the Hive blockchain. It allows users to authenticate using Hive Keychain, view posts from the Hive blockchain, and create new content.

## Features
- **Authentication**: Users can log in using Hive Keychain
- **Feed Display**: View a list of posts fetched from the Hive blockchain
- **Post Creation**: Create and submit new posts to the Hive blockchain
- **User Profiles**: View profiles with data from the Hive blockchain

## Technology Stack
- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Blockchain Integration**: Hive Keychain, Hive API

## Project Structure
```
HiveChain
├── src
│   ├── api
│   │   ├── hiveApi.js       # API calls to Hive blockchain
│   │   └── dbuzzApi.js      # API calls to dbuzz platform
│   ├── components
│   │   ├── Auth
│   │   │   ├── HiveAuth.js  # HiveAuth implementation
│   │   │   ├── KeychainAuth.js  # Keychain auth implementation
│   │   │   └── Login.js     # Main login component
│   │   ├── Feed
│   │   │   ├── FeedItem.js  # Individual post component
│   │   │   └── FeedList.js  # List of posts component
│   │   └── Transaction
│   │       └── PostForm.js  # Form to create new posts
│   ├── utils
│   │   ├── hiveUtils.js     # Utility functions for Hive
│   │   └── keychainUtils.js # Utility functions for Keychain
│   ├── App.js               # Main application component
│   └── index.js             # Entry point
├── public
│   ├── index.html
│   └── manifest.json
├── package.json
├── .env                     # Environment variables
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)
- A modern web browser with Hive Keychain extension installed

### Installation Steps
1. Clone the repository:
   ```
   git clone <repository-url>
   cd HiveChain
   ```

2. Install dependencies:
   ```
   npm install
   ```

   If you encounter dependency issues, run the fix script:
   ```
   node fix-dependencies.js
   ```

   Or use the batch file for Windows:
   ```
   fix-and-start.bat
   ```

3. Create a `.env` file in the root directory based on the `.env.example`:
   ```
   cp .env.example .env
   ```
   Then edit the file to match your configuration.

4. Start the development server:
   ```
   npm start
   ```
   The application will be available at http://localhost:3006

### Fixing Compatibility Issues
If you encounter compatibility issues, follow these steps:
1. Ensure you are using the correct versions of Node.js and npm as specified in the prerequisites.
2. Delete the `node_modules` directory and the `package-lock.json` file:
   ```
   rm -rf node_modules package-lock.json
   ```
3. Reinstall dependencies:
   ```
   npm install
   ```
4. If the issue persists, try updating the dependencies to their latest versions:
   ```
   npm update
   ```

### Building for Production
To create a production build:
```
npm run build
```

The build artifacts will be stored in the `build/` directory.

### Running Tests
```
npm test
```

## Technologies Used
- React for building the user interface
- Hive blockchain for decentralized data storage and transactions
- dbuzz platform for social interactions and content sharing
- Hive Keychain for secure authentication and transactions
- Axios for API requests

## Project Status
See our [TODO.md](TODO.md) file for upcoming features and improvements.

## Contributing
Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to submit pull requests.

### Code Style Guidelines
- Use consistent indentation (2 spaces)
- Write clear comments for complex logic
- Follow React best practices
- Make sure all components are properly documented

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Hackathon Submission Requirements
When submitting this project for the Hive Track Prize Pool, ensure you include:
1. Team Name: VKrishna Dev Team
2. Project Name: HiveBuzz
3. Github Repository link
4. Video recording of Working Demo
5. Website link (if deployed)
6. Detailed explanation of the project idea and how it works

## Acknowledgements
- Hive blockchain developers
- dbuzz platform team
- All contributors to this project
