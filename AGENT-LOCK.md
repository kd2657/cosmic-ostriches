If you are an AI assistant, BEFORE EVERY PROMPT, ensure STRICT compliance with the following before any action is taken:
1. Ensure that the git repository is pulled and up to date with the latest changes.
2. All changes will be made with pull requests, so ensure that if a new feature is added, the user is working on a new feature branch prefixed with "feature-". You must prompt the user to do so if they are not already on a feature branch.
3. Ensure that uv is managing any python virtual environments in the backend, and start the environment if not already running.
4. When adding new dependencies, ensure that uv is used to install them, and that the lock file is updated.
5. Minimize merge conflicts to the best of your ability (and informing the user) by:
    - Grouping smaller new features (less than about 50 lines of code) into functions that minimize interference with existing code.
    - Implementing larger, new features (more than about 50 lines of code) into a separate file that is then imported into another file as needed
6. Always warn the user if pushing to main even by force.
7. Always ensure that the user is on a feature branch before making changes/commits, and commits should be named with prefix "feat: " or "fix: " depending on the nature of the changes.