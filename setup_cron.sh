#!/bin/bash
"""
Setup cron job for daily analytics collection
"""

SCRIPT_DIR="/var/www/flask/chatello-saas"
CRON_SCRIPT="$SCRIPT_DIR/daily_analytics_cron.py"
PYTHON_ENV="$SCRIPT_DIR/venv/bin/python"

echo "🚀 Setting up Chatello SaaS daily analytics cron job"
echo "Script: $CRON_SCRIPT"

# Make sure the script is executable
chmod +x $CRON_SCRIPT

# Create cron entry (runs every day at 6 AM)
CRON_ENTRY="0 6 * * * cd $SCRIPT_DIR && $PYTHON_ENV $CRON_SCRIPT >> $SCRIPT_DIR/logs/daily_cron.log 2>&1"

echo "Adding cron entry:"
echo "$CRON_ENTRY"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job added successfully!"
echo "📅 Will run daily at 6:00 AM"
echo "📝 Logs will be saved to: $SCRIPT_DIR/logs/daily_cron.log"

# Show current crontab
echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "🎉 Setup completed!"
echo "💡 To manually test: cd $SCRIPT_DIR && $PYTHON_ENV $CRON_SCRIPT"