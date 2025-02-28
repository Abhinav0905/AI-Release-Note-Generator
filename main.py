import requests
import re
import pandas as pd
from jira import JIRA

# Confluence API details
base_url = "https://abc.atlassian.net/wiki"
page_id = '4836884481'
username = ""
api_token = ""

# JIRA API details
jira_base_url = "https://abc.atlassian.net"
jira_username = ""
jira_api_token = ""

def connect_to_jira():
    try:
        jira = JIRA(server=jira_base_url, basic_auth=(jira_username, jira_api_token))
        return jira
    except Exception as e:
        print(f"Failed to connect to JIRA: {str(e)}")
        return None

def generate_customer_release_notes(ticket_ids):
    jira = connect_to_jira()
    if not jira:
        return []
    
    customer_notes = []
    for ticket_id in ticket_ids:
        try:
            issue = jira.issue(ticket_id)
            
            # Extract relevant fields
            summary = issue.fields.summary
            description = issue.fields.description or ""
            components = [c.name for c in issue.fields.components]
            issue_type = issue.fields.issuetype.name
            
            # Look for customer impact or release note field
            # Assuming there's a custom field for customer-facing notes
            customer_impact = getattr(issue.fields, 'customfield_customer_impact', '')
            
            # Create a customer-friendly note
            note = {
                'ticket_id': ticket_id,
                'type': issue_type,
                'component': ', '.join(components),
                'summary': summary,
                'customer_impact': customer_impact if customer_impact else 'No customer impact specified',
                'category': 'Enhancement' if issue_type in ['Story', 'Improvement'] else 'Bug Fix'
            }
            
            customer_notes.append(note)
            
        except Exception as e:
            print(f"Error processing ticket {ticket_id}: {str(e)}")
            continue
    
    return customer_notes

def export_customer_release_notes(customer_notes):
    if not customer_notes:
        print("No customer release notes to export")
        return
    
    # Organize notes by category
    enhancements = []
    bug_fixes = []
    
    for note in customer_notes:
        if note['category'] == 'Enhancement':
            enhancements.append(note)
        else:
            bug_fixes.append(note)
    
    # Create DataFrame for customer-facing release notes
    customer_data = []
    
    # Process enhancements
    for note in enhancements:
        customer_data.append({
            'Category': 'Enhancement',
            'Component': note['component'],
            'Description': f"{note['summary']}\n{note['customer_impact']}",
            'Reference': note['ticket_id']
        })
    
    # Process bug fixes
    for note in bug_fixes:
        customer_data.append({
            'Category': 'Bug Fix',
            'Component': note['component'],
            'Description': f"{note['summary']}\n{note['customer_impact']}",
            'Reference': note['ticket_id']
        })
    
    df_customer_notes = pd.DataFrame(customer_data)
    df_customer_notes.to_csv('customer_release_notes_7_2_30.csv', index=False)
    print("Customer-facing release notes have been saved to 'customer_release_notes_7_2_30.csv'")

# Fetch page content from Confluence
def fetch_confluence_page_content(base_url, page_id, username, api_token):
    url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage"
    print(f"Fetching URL: {url}")  # Debug information
    response = requests.get(url, auth=(username, api_token))
    if response.status_code == 200:
        content = response.json()['body']['storage']['value']
        return content
    else:
        print(f"Response Status Code: {response.status_code}")  # Debug information
        print(f"Response Text: {response.text}")  # Debug information
        raise Exception(f"Failed to fetch Confluence page content: {response.status_code}")

# Extract sections from the Confluence page content
def extract_sections(content):
    summary_of_changes_start = content.find("Summary of Changes")
    enhancements_improvements_start = content.find("Enhancements & Improvements")
    bug_fixes_start = content.find("Bug Fixes")
    known_issues_start = content.find("Known Issues")

    print("Indices found:")
    print(f"Summary of Changes start: {summary_of_changes_start}")
    print(f"Enhancements & Improvements start: {enhancements_improvements_start}")
    print(f"Bug Fixes start: {bug_fixes_start}")
    print(f"Known Issues start: {known_issues_start}")

    summary_of_changes_text = content[summary_of_changes_start:enhancements_improvements_start].strip()
    enhancements_improvements_text = content[enhancements_improvements_start:bug_fixes_start].strip()
    bug_fixes_text = content[bug_fixes_start:known_issues_start].strip()
    
    print("Extracted Sections:")
    print("Summary of Changes Section:")
    print(summary_of_changes_text[:1000])  # Print the first 1000 characters for debugging
    print("\nEnhancements & Improvements Section:")
    print(enhancements_improvements_text[:1000])  # Print the first 1000 characters for debugging
    print("\nBug Fixes Section:")
    print(bug_fixes_text[:1000])  # Print the first 1000 characters for debugging
    
    return summary_of_changes_text, enhancements_improvements_text, bug_fixes_text

# Extract and process issues
def extract_summary_of_changes(section_text):
    issues = re.findall(r'ENG-\d+.*?(?=<p>ENG-\d+|</p>)', section_text, re.DOTALL)
    processed_issues = []
    for issue in issues:
        parts = re.split(r'\s-\s', issue.strip())
        ticket = parts[0].strip()
        if len(parts) > 1:
            feature = parts[0].strip()
            change = parts[1].strip() if len(parts) > 1 else ""
            processed_issues.append((ticket, feature, change))
        else:
            processed_issues.append((ticket, parts[0], ""))
    return processed_issues

# Categorize issues by component
def categorize_detailed_issues(issues, components_info):
    for issue in issues:
        for component in components_info:
            if component.lower() in issue[1].lower():
                components_info[component].append(issue)
                break

# Define components
components = [
    "rts 7.x component", "Event Processor", "Rest API", "rest API component",
    "rIS component / Event Processor", "mobile Apk", "grpc", "rts-oms-processor",
    "rim Component", "rts-sr-cr"
]

# Create a dictionary to store information by component
components_info_detailed = {component: [] for component in components}

# Fetch and process data
content = fetch_confluence_page_content(base_url, page_id, username, api_token)
summary_of_changes_text, enhancements_improvements_text, bug_fixes_text = extract_sections(content)
summary_of_changes_detailed = extract_summary_of_changes(summary_of_changes_text)
enhancements_improvements_detailed = extract_summary_of_changes(enhancements_improvements_text)
bug_fixes_detailed = extract_summary_of_changes(bug_fixes_text)
all_detailed_issues = summary_of_changes_detailed + enhancements_improvements_detailed + bug_fixes_detailed
categorize_detailed_issues(all_detailed_issues, components_info_detailed)

# Prepare the final summary
summary_data_detailed = []
for component, changes in components_info_detailed.items():
    feature_updated = "; ".join([change[1] for change in changes])
    change_in_feature = "; ".join([change[2] for change in changes if change[2]])
    summary_data_detailed.append([component, feature_updated, change_in_feature])

# Convert to DataFrame
df_summary_detailed = pd.DataFrame(summary_data_detailed, columns=["Module Affected", "Feature of the module that has been updated", "Change in the feature"])

# Save the DataFrame to a CSV file
df_summary_detailed.to_csv('release_note_summary_7_2_30.csv', index=False)

print("Summary data has been saved to 'release_note_summary_7_2_30.csv'")

# Extract ticket IDs from all detailed issues
ticket_ids = [issue[0] for issue in all_detailed_issues]

# Generate and export customer-facing release notes
customer_notes = generate_customer_release_notes(ticket_ids)
export_customer_release_notes(customer_notes)