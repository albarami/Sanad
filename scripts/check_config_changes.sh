#!/bin/bash
# CI script to check for config changes and require CHANGELOG entry
# Usage: ./scripts/check_config_changes.sh

set -e

echo "🔍 Checking for config directory changes..."

# Check if config directory has changes
if git diff --name-only HEAD~1 HEAD | grep -q "^config/"; then
    echo "⚠️  Config directory changes detected!"
    
    # List changed config files
    echo "Changed config files:"
    git diff --name-only HEAD~1 HEAD | grep "^config/" | sed 's/^/  - /'
    
    # Check if CHANGELOG.md has been updated
    if git diff --name-only HEAD~1 HEAD | grep -q "CHANGELOG.md"; then
        echo "✅ CHANGELOG.md has been updated"
        
        # Verify CHANGELOG contains config-related entry
        if git diff HEAD~1 HEAD CHANGELOG.md | grep -iq "config\|configuration"; then
            echo "✅ CHANGELOG.md contains config-related entry"
        else
            echo "❌ CHANGELOG.md updated but no config-related entry found"
            echo "Please add a config-related entry to CHANGELOG.md"
            exit 1
        fi
    else
        echo "❌ Config changes detected but CHANGELOG.md not updated"
        echo "Please update CHANGELOG.md with details about config changes"
        exit 1
    fi
    
    # Compute and log config hash for reference
    echo "📋 Computing config hash for reference..."
    if command -v python3 &> /dev/null; then
        python3 -m backend.core.config_hash || echo "Warning: Could not compute config hash"
    else
        echo "Warning: Python3 not available for config hash computation"
    fi
    
else
    echo "✅ No config directory changes detected"
fi

echo "🎯 Config change check completed successfully"
