#!/bin/bash
# Script to add, commit, and push changes to GitHub

# Navigate to the script's directory (your project directory)
cd "$(dirname "$0")"

echo "Adding all changes..."
git add .

echo "Committing changes..."
# You can change this default commit message if you like
COMMIT_MESSAGE="Update application code - auto-script"
git commit -m "$COMMIT_MESSAGE"

echo "Pushing to origin main..."
git push origin main

echo "Git push complete!" 