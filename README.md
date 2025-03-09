# HiveBuzz

A Flask-based web application for interacting with the Hive blockchain.

## Overview
HiveBuzz is a decentralized social media application built on the Hive blockchain. It allows users to authenticate using Hive Keychain, view posts from the Hive blockchain, and create new content.

## Features
- **Authentication**: Users can log in using Hive Keychain
- **Feed Display**: View a list of posts fetched from the Hive blockchain
- **Post Creation**: Create and submit new posts to the Hive blockchain
- **User Profiles**: View profiles with data from the Hive blockchain
- Login with HiveKeychain, HiveSigner, or HiveAuth
- View and create Hive blockchain content
- Responsive design with light/dark theme
- User wallet management
- SQLite database for caching and local data storage

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
- Python 3.8 or higher
- pip (Python package manager)
- Git
- A modern web browser with Hive Keychain extension installed

### Installation Steps
1. Clone the repository:
   ```
   git clone <repository-url>
   cd HiveChain
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory based on the `.env.example`:
   ```
   cp .env.example .env
   ```
   Then edit the file to match your configuration.

5. Run the setup script:
   ```
   python setup.py
   ```

6. Start the development server:
   ```
   flask run
   ```
   The application will be available at http://localhost:5000/

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

## Database Management

HiveBuzz uses SQLite for database storage. The database file is created at `hivebuzz.db` in the project root directory.

### Database Schema

- **users** - User information
- **sessions** - Session management
- **user_preferences** - User preferences and settings
- **cached_posts** - Post caching
- **activity_logs** - User activity tracking

### Database Tools

For database management, use the `db_manager.py` CLI tool:

```bash
# Initialize the database
python db_manager.py init

# Show database statistics
python db_manager.py stats

# Clear expired sessions
python db_manager.py clear-sessions

# Show information about a specific user
python db_manager.py user-info <username>

# Clean up old data (older than 30 days)
python db_manager.py cleanup --days=30

# Optimize database storage
python db_manager.py vacuum

# Backup database to SQL file
python db_manager.py backup
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
