# import requests
# import json
# import os
# from datetime import datetime
# from bs4 import BeautifulSoup

# SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
# STATUS_PAGE_URL = 'https://status.gohighlevel.com/'
# CACHE_FILE = 'status_cache.json'

# def load_cache():
#     """Load the previous status from cache"""
#     try:
#         with open(CACHE_FILE, 'r') as f:
#             return json.load(f)
#     except FileNotFoundError:
#         return {}

# def save_cache(data):
#     """Save current status to cache"""
#     with open(CACHE_FILE, 'w') as f:
#         json.dump(data, f, indent=2)

# def fetch_status():
#     """Fetch current status from GoHighLevel status page"""
#     try:
#         response = requests.get(STATUS_PAGE_URL, timeout=10)
#         response.raise_for_status()
        
#         soup = BeautifulSoup(response.text, 'html.parser')
        
#         # Extract overall status
#         status_indicator = soup.find('span', class_='status')
#         overall_status = status_indicator.text.strip() if status_indicator else 'Unknown'
        
#         # Extract any active incidents
#         incidents = []
#         incident_elements = soup.find_all('div', class_='incident-title') or soup.find_all('div', class_='unresolved-incident')
        
#         for incident in incident_elements:
#             title = incident.get_text(strip=True)
#             incidents.append(title)
        
#         return {
#             'overall_status': overall_status,
#             'incidents': incidents,
#             'timestamp': datetime.now().isoformat()
#         }
#     except Exception as e:
#         print(f"Error fetching status: {e}")
#         return None

# def send_slack_notification(message, color='warning'):
#     """Send notification to Slack"""
#     if not SLACK_WEBHOOK_URL:
#         print("No Slack webhook URL configured")
#         return
    
#     # Color codes: good (green), warning (yellow), danger (red)
#     colors = {
#         'operational': 'good',
#         'degraded': 'warning',
#         'outage': 'danger',
#         'warning': 'warning'
#     }
    
#     payload = {
#         "attachments": [{
#             "color": colors.get(color, 'warning'),
#             "blocks": [
#                 {
#                     "type": "header",
#                     "text": {
#                         "type": "plain_text",
#                         "text": "🚨 GoHighLevel Status Update"
#                     }
#                 },
#                 {
#                     "type": "section",
#                     "text": {
#                         "type": "mrkdwn",
#                         "text": message
#                     }
#                 },
#                 {
#                     "type": "context",
#                     "elements": [
#                         {
#                             "type": "mrkdwn",
#                             "text": f"🔗 <{STATUS_PAGE_URL}|View Status Page> • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
#                         }
#                     ]
#                 }
#             ]
#         }]
#     }
    
#     try:
#         response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
#         response.raise_for_status()
#         print("Slack notification sent successfully")
#     except Exception as e:
#         print(f"Error sending Slack notification: {e}")

# def main():
#     print("Checking GoHighLevel status...")
    
#     current_status = fetch_status()
#     if not current_status:
#         print("Failed to fetch status")
#         return
    
#     previous_status = load_cache()
    
#     # Check if this is first run
#     if not previous_status:
#         print("First run - initializing cache")
#         save_cache(current_status)
#         # Send initial status
#         message = f"*Status Monitor Started*\n\nCurrent Status: `{current_status['overall_status']}`"
#         if current_status['incidents']:
#             message += f"\n\n⚠️ *Active Incidents:*\n" + "\n".join([f"• {inc}" for inc in current_status['incidents']])
#         send_slack_notification(message, 'warning')
#         return
    
#     # Detect changes
#     status_changed = current_status['overall_status'] != previous_status.get('overall_status')
#     incidents_changed = set(current_status['incidents']) != set(previous_status.get('incidents', []))
    
#     if status_changed or incidents_changed:
#         print("Status change detected!")
        
#         message_parts = []
        
#         # Status change
#         if status_changed:
#             old_status = previous_status.get('overall_status', 'Unknown')
#             new_status = current_status['overall_status']
#             message_parts.append(f"*Status Changed:* `{old_status}` → `{new_status}`")
        
#         # Incident changes
#         if incidents_changed:
#             new_incidents = set(current_status['incidents']) - set(previous_status.get('incidents', []))
#             resolved_incidents = set(previous_status.get('incidents', [])) - set(current_status['incidents'])
            
#             if new_incidents:
#                 message_parts.append(f"\n⚠️ *New Incidents:*\n" + "\n".join([f"• {inc}" for inc in new_incidents]))
            
#             if resolved_incidents:
#                 message_parts.append(f"\n✅ *Resolved:*\n" + "\n".join([f"• {inc}" for inc in resolved_incidents]))
        
#         # Current active incidents
#         if current_status['incidents']:
#             message_parts.append(f"\n📋 *Currently Active:*\n" + "\n".join([f"• {inc}" for inc in current_status['incidents']]))
        
#         message = "\n".join(message_parts)
        
#         # Determine color based on status
#         color = 'warning'
#         if 'operational' in current_status['overall_status'].lower():
#             color = 'operational'
#         elif 'outage' in current_status['overall_status'].lower() or 'down' in current_status['overall_status'].lower():
#             color = 'outage'
        
#         send_slack_notification(message, color)
#         save_cache(current_status)
#     else:
#         print("No changes detected")
#         save_cache(current_status)

# if __name__ == '__main__':
#     main()
