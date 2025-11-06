import requests
import json
import os
from datetime import datetime

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
STATUS_PAGE_URL = 'https://status.gohighlevel.com/'
STATUS_API_URL = 'https://status.gohighlevel.com/api/v2/summary.json'
CACHE_FILE = 'status_cache.json'

def load_cache():
    """Load the previous status from cache"""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_cache(data):
    """Save current status to cache"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def fetch_status():
    """Fetch current status from GoHighLevel status page API"""
    try:
        response = requests.get(STATUS_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract overall status
        status_info = data.get('status', {})
        overall_status = status_info.get('description', 'Unknown')
        status_indicator = status_info.get('indicator', 'none')  # none, minor, major, critical
        
        # Extract component statuses
        components = []
        for component in data.get('components', []):
            components.append({
                'name': component.get('name', ''),
                'status': component.get('status', 'unknown'),
                'description': component.get('description', '')
            })
        
        # Extract unresolved incidents
        incidents = []
        for incident in data.get('incidents', []):
            if incident.get('status') not in ['resolved', 'postmortem']:
                incidents.append({
                    'name': incident.get('name', ''),
                    'status': incident.get('status', ''),
                    'impact': incident.get('impact', ''),
                    'created_at': incident.get('created_at', ''),
                    'shortlink': incident.get('shortlink', '')
                })
        
        # Extract scheduled maintenances
        maintenances = []
        for maintenance in data.get('scheduled_maintenances', []):
            if maintenance.get('status') in ['scheduled', 'in_progress']:
                maintenances.append({
                    'name': maintenance.get('name', ''),
                    'status': maintenance.get('status', ''),
                    'scheduled_for': maintenance.get('scheduled_for', ''),
                    'shortlink': maintenance.get('shortlink', '')
                })
        
        return {
            'overall_status': overall_status,
            'status_indicator': status_indicator,
            'components': components,
            'incidents': incidents,
            'maintenances': maintenances,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error fetching status: {e}")
        return None

def format_component_status(components):
    """Format component statuses for Slack message"""
    if not components:
        return ""
    
    status_emoji = {
        'operational': '✅',
        'degraded_performance': '⚠️',
        'partial_outage': '🟡',
        'major_outage': '🔴',
        'under_maintenance': '🔧'
    }
    
    lines = []
    for comp in components:
        emoji = status_emoji.get(comp['status'], '❓')
        status_text = comp['status'].replace('_', ' ').title()
        lines.append(f"{emoji} *{comp['name']}*: {status_text}")
    
    return "\n".join(lines)

def send_slack_notification(message, color='warning'):
    """Send notification to Slack"""
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook URL configured")
        return
    
    # Color codes: good (green), warning (yellow), danger (red)
    payload = {
        "attachments": [{
            "color": color,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 GoHighLevel Status Update"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🔗 <{STATUS_PAGE_URL}|View Status Page> • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        }
                    ]
                }
            ]
        }]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print("Slack notification sent successfully")
    except Exception as e:
        print(f"Error sending Slack notification: {e}")

def main():
    print("Checking GoHighLevel status...")
    
    current_status = fetch_status()
    if not current_status:
        print("Failed to fetch status")
        return
    
    previous_status = load_cache()
    
    # Check if this is first run
    if not previous_status:
        print("First run - initializing cache")
        save_cache(current_status)
        
        # Send initial status
        message_parts = [f"*Status Monitor Started*\n\n📊 *Overall Status:* `{current_status['overall_status']}`"]
        
        # Add component statuses
        if current_status['components']:
            message_parts.append(f"\n*Component Status:*\n{format_component_status(current_status['components'])}")
        
        # Add active incidents
        if current_status['incidents']:
            incident_text = "\n".join([f"• *{inc['name']}* ({inc['impact']}) - {inc['status']}" 
                                      for inc in current_status['incidents']])
            message_parts.append(f"\n⚠️ *Active Incidents:*\n{incident_text}")
        
        # Add scheduled maintenances
        if current_status['maintenances']:
            maint_text = "\n".join([f"• *{m['name']}* - {m['status']}" 
                                   for m in current_status['maintenances']])
            message_parts.append(f"\n🔧 *Scheduled Maintenance:*\n{maint_text}")
        
        message = "\n".join(message_parts)
        color = 'good' if current_status['status_indicator'] == 'none' else 'warning'
        send_slack_notification(message, color)
        return
    
    # Detect changes
    status_changed = current_status['overall_status'] != previous_status.get('overall_status')
    
    # Check for new or resolved incidents
    prev_incident_names = {inc['name'] for inc in previous_status.get('incidents', [])}
    curr_incident_names = {inc['name'] for inc in current_status['incidents']}
    new_incidents = curr_incident_names - prev_incident_names
    resolved_incidents = prev_incident_names - curr_incident_names
    
    # Check for component status changes
    prev_components = {c['name']: c['status'] for c in previous_status.get('components', [])}
    curr_components = {c['name']: c['status'] for c in current_status['components']}
    changed_components = []
    for name, status in curr_components.items():
        if name in prev_components and prev_components[name] != status:
            changed_components.append((name, prev_components[name], status))
    
    # If any changes detected, send notification
    if status_changed or new_incidents or resolved_incidents or changed_components:
        print("Status change detected!")
        
        message_parts = []
        
        # Overall status change
        if status_changed:
            old_status = previous_status.get('overall_status', 'Unknown')
            new_status = current_status['overall_status']
            message_parts.append(f"*Overall Status Changed:*\n`{old_status}` → `{new_status}`")
        
        # New incidents
        if new_incidents:
            incidents_detail = []
            for inc in current_status['incidents']:
                if inc['name'] in new_incidents:
                    incidents_detail.append(f"• *{inc['name']}* ({inc['impact']})\n  Status: {inc['status']}")
            message_parts.append(f"\n🚨 *New Incidents:*\n" + "\n".join(incidents_detail))
        
        # Resolved incidents
        if resolved_incidents:
            message_parts.append(f"\n✅ *Resolved Incidents:*\n" + "\n".join([f"• {inc}" for inc in resolved_incidents]))
        
        # Component changes
        if changed_components:
            comp_changes = []
            for name, old, new in changed_components:
                comp_changes.append(f"• *{name}*: {old} → {new}")
            message_parts.append(f"\n📊 *Component Status Changes:*\n" + "\n".join(comp_changes))
        
        # Current component statuses
        message_parts.append(f"\n*Current Status:*\n{format_component_status(current_status['components'])}")
        
        message = "\n".join(message_parts)
        
        # Determine color based on status indicator
        color_map = {
            'none': 'good',
            'minor': 'warning',
            'major': 'danger',
            'critical': 'danger'
        }
        color = color_map.get(current_status['status_indicator'], 'warning')
        
        send_slack_notification(message, color)
        save_cache(current_status)
    else:
        print("No changes detected")
        save_cache(current_status)

if __name__ == '__main__':
    main()
