#!/bin/bash

# Function to set an environment variable
set_env_var() {
  local var_name="$1"
  local var_value="$2"
  echo "export $var_name=\"$var_value\"" >> ~/.bashrc  # Or ~/.zshrc, ~/.bash_profile, etc.
  echo "export $var_name=\"$var_value\"" >> ~/.profile # for good measure add it here too

  # source the file to make change effective immediately in current shell.
  # Important:  This only affects the current shell and its children.
  source ~/.bashrc
}

# Function to clear an environment variable
clear_env_var() {
  local var_name="$1"
  sed -i -E "/^export $var_name=/d" ~/.bashrc  # Remove line from .bashrc
  sed -i -E "/^export $var_name=/d" ~/.profile # Remove the line from .profile

  # Unset in current shell (important!)
  unset "$var_name"
}


# Check if the --clear flag is provided
if [[ "$1" == "--clear" ]]; then
  echo "Clearing CANVAS_API_KEY and CANVAS_COURSE_URL environment variables..."
  clear_env_var "CANVAS_API_KEY"
  clear_env_var "CANVAS_COURSE_URL"
  echo "Variables cleared.  You may need to restart your shell/terminal."
  exit 0
fi

# Get API key
while true; do
  read -r -p "Enter your Canvas API key: " api_key
  if [[ -n "$api_key" ]]; then
    break
  else
    echo "API key cannot be empty."
  fi
done

# Get course URL
while true; do
  read -r -p "Enter your Canvas course URL (e.g., https://canvas.example.com/courses/12345): " course_url
  if [[ -n "$course_url" ]]; then
    # Validate the course URL format (basic check)
    if [[ "$course_url" =~ ^https://[^/]+/courses/[0-9]+$ ]]; then
      break
    else
      echo "Invalid course URL format. It should be like https://canvas.example.com/courses/12345"
    fi
  else
    echo "Course URL cannot be empty."
  fi
done

echo "Setting environment variables..."

# Set the environment variables persistently
set_env_var "CANVAS_API_KEY" "$api_key"
set_env_var "CANVAS_COURSE_URL" "$course_url"

echo "Environment variables set successfully."
echo "You may need to restart your shell/terminal for the changes to take effect."

exit 0