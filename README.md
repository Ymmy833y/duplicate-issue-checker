# Duplicate Issue Checker

The Duplicate Issue Checker is a web application designed to retrieve and analyze issues and pull request comments from a specified GitHub repository. The application helps users quickly identify duplicate issues, thereby reducing redundancy and ensuring streamlined issue management.

![Screenshot](/branding//duplicate-issue-checker-index.png)

## Features

- **Retrieve Issues and PRs**: Pulls all comments from issues and PRs in a GitHub repository.
- **Duplicate Detection**: Uses text similarity analysis to identify potential duplicate issues.
- **Similarity Threshold**: Provides similarity scores and a categorization of similarity (e.g., "Moderate similarity," "Low similarity").
- **User-Friendly Interface**: Displays results with details, including similarity threshold and descriptions of potential duplicates.
- **Easy GitHub Integration**: Works seamlessly with any public GitHub repository, allowing users to specify the repository URL, issue title, and description for precise results.

## Screenshots
### Duplicate Issue Results
![Screenshot](/branding//duplicate-issue-checker-search.png)

## Installation

To run the Duplicate Issue Checker locally, follow these steps:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Ymmy833y/duplicate-issue-checker.git
   cd duplicate-issue-checker
   ```

2. **Set up a virtual environment** (optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up GitHub API Access**:

   - Make sure to set up a GitHub personal access token with the necessary permissions.
   - Configure the application to use this token by setting it in your environment variables.

5. **Run the application**:

   ```bash
   python .\run.py
   ```
6. **Install npm dependencies (for the frontend)**:

   ```bash
   npm install
   ```
7. **Start the frontend**:

   ```bash
   npm run start
   ```
8. The application will be accessible at http://127.0.0.1:5000.

## Usage

1. Enter the GitHub repository URL, issue title, and optional description in the form on the search page.
2. Click "Search" to retrieve related issues and check for duplicates.
3. View the results, which will display similarity scores and the level of similarity for each potential duplicate issue.

## How It Works

The app leverages sentence_transformers for advanced natural language processing (NLP) in similarity analysis. By converting text into embeddings and calculating similarity scores, it effectively identifies duplicates or related issues based on the semantic meaning of text. This method ensures a robust comparison that goes beyond simple keyword matching.

## Technologies Used

- **Backend**: Flask
- **Frontend**: Tailwind CSS for styling
- **GitHub API**: To fetch issues and PRs
- **Natural Language Processing (NLP)**: For similarity detection

## License

This project is open source and available under the [MIT License](LICENSE).
