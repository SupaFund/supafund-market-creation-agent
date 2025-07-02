#!/bin/bash

# setup_check.sh
# A script to verify that the environment is correctly set up to run the
# Supafund Market Creation Agent.

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "--- Running Supafund Market Creation Agent Environment Check ---"
echo ""

ALL_CHECKS_PASSED=true

# --- Check 1: Verify 'poetry' command ---
echo -n "1. Checking for 'poetry' command... "
if command -v poetry &> /dev/null
then
    echo -e "${GREEN}OK${NC}"
    POETRY_PATH=$(command -v poetry)
    echo "   -> Found at: ${POETRY_PATH}"
else
    echo -e "${RED}Failed${NC}"
    echo -e "   ${YELLOW}Action required:${NC} 'poetry' command not found."
    echo "   Please install Poetry by following the instructions at:"
    echo "   https://python-poetry.org/docs/#installation"
    echo "   After installation, ensure its path is in your system's PATH, or"
    echo "   find its absolute path using 'which poetry' and set it in the .env file as POETRY_PATH."
    echo ""
    ALL_CHECKS_PASSED=false
fi

# --- Check 2: Verify .env file ---
echo -n "2. Checking for .env file... "
if [ -f .env ]; then
    echo -e "${GREEN}OK${NC}"
    
    # --- Check 3: Verify required variables in .env ---
    echo "3. Checking for required variables in .env file:"
    
    # Source .env file to load its variables for this script
    set -a
    source .env
    set +a

    REQUIRED_VARS=( "SUPABASE_URL" "SUPABASE_KEY" "OMEN_PRIVATE_KEY" "OMEN_SCRIPT_PROJECT_PATH" )
    MISSING_VARS=()

    for VAR in "${REQUIRED_VARS[@]}"; do
        echo -n "   - Checking for ${VAR}... "
        # Check if the variable is not set or is empty
        if [ -z "${!VAR}" ]; then
            echo -e "${RED}Missing or empty${NC}"
            MISSING_VARS+=("$VAR")
            ALL_CHECKS_PASSED=false
        else
            echo -e "${GREEN}OK${NC}"
        fi
    done

    if [ ${#MISSING_VARS[@]} -ne 0 ]; then
        echo -e "   ${YELLOW}Action required:${NC} Please define the following variable(s) in your .env file: ${MISSING_VARS[*]}"
        echo ""
    fi

else
    echo -e "${RED}Failed${NC}"
    echo -e "   ${YELLOW}Action required:${NC} The .env file does not exist."
    echo "   Please create it by copying the required variables. It should contain:"
    echo "   ---"
    echo "   SUPABASE_URL=\"...\""
    echo "   SUPABASE_KEY=\"...\""
    echo "   OMEN_PRIVATE_KEY=\"...\""
    echo "   OMEN_SCRIPT_PROJECT_PATH=\"...\""
    echo "   POETRY_PATH=\"...\" # Optional, but recommended"
    echo "   ---"
    echo ""
    ALL_CHECKS_PASSED=false
fi


# --- Final Summary ---
echo "--- Check Complete ---"
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}Success! Your environment appears to be set up correctly.${NC}"
else
    echo -e "${RED}Failure. Please address the issues listed above and run this script again.${NC}"
    exit 1
fi

exit 0 