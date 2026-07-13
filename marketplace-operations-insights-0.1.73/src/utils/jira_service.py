import os
from atlassian import Jira
import streamlit as st

class JiraService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JiraService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Jira client with credentials from Streamlit secrets"""
        self.jira = None
        try:
            # Get credentials from Streamlit secrets
            jira_user = st.secrets["jira"]["username"]
            jira_api_token = st.secrets["jira"]["password"]
            self.jira_server = st.secrets["jira"]["url"]
            
            # Initialize Jira client - Atlassian style! 🎸
            self.jira = Jira(
                url=self.jira_server,
                username=jira_user,
                password=jira_api_token,
                cloud=True  # Set to True for Jira Cloud, False for Server
            )
        except Exception as e:
            st.error(f"Failed to initialize Jira client: {str(e)}")
    
    def create_ticket(self, project_key, summary, description, issue_type, labels=None, components=None, **custom_fields):
        """
        Create a Jira ticket with the given parameters
        
        Args:
            project_key (str): The project key where the ticket should be created
            summary (str): Ticket summary/title
            description (str): Detailed ticket description
            issue_type (str): Type of issue (default: Task)
            labels (list): List of labels to add to the ticket
            components (list): List of component names to add to the ticket
            **custom_fields: Additional custom fields to add to the ticket
        
        Returns:
            str: URL of the created ticket or None if creation failed
        """
        if not self.jira:
            st.error("Jira client not initialized")
            return None
            
        try:
            # Prepare ticket fields
            issue_dict = {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type}
            }
            
            # Add optional fields if provided
            if labels:
                issue_dict["labels"] = labels
                
            if components:
                issue_dict["components"] = [{"name": c} for c in components]
            
            # Add any custom fields
            issue_dict.update(custom_fields)
            
            # Create the ticket
            new_issue = self.jira.issue_create(fields=issue_dict)
            
            # Return the ticket URL
            issue_key = new_issue.get("key")
            return f"{self.jira_server}/browse/{issue_key}"
            
        except Exception as e:
            st.error(f"Failed to create Jira ticket: {str(e)}")
            return None
    
    def update_ticket(self, ticket_key, **fields):
        """
        Update an existing Jira ticket
        
        Args:
            ticket_key (str): The key of the ticket to update
            **fields: Fields to update (e.g., summary="New Summary", description="New Description")
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        if not self.jira:
            st.error("Jira client not initialized")
            return False
            
        try:
            self.jira.issue_update(ticket_key, fields=fields)
            return True
        except Exception as e:
            st.error(f"Failed to update Jira ticket: {str(e)}")
            return False
    
    def add_comment(self, ticket_key, comment):
        """
        Add a comment to an existing Jira ticket
        
        Args:
            ticket_key (str): The key of the ticket to comment on
            comment (str): The comment text
            
        Returns:
            bool: True if comment was added successfully, False otherwise
        """
        if not self.jira:
            st.error("Jira client not initialized")
            return False
            
        try:
            self.jira.issue_add_comment(ticket_key, comment)
            return True
        except Exception as e:
            st.error(f"Failed to add comment: {str(e)}")
            return False

    def get_issue(self, ticket_key):
        """
        Get issue details
        """
        if not self.jira:
            st.error("Jira client not initialized")
            return None
            
        try:
            return self.jira.issue(ticket_key)
        except Exception as e:
            st.error(f"Failed to get issue: {str(e)}")
            return None

    def check_custom_fields(self, project_key, custom_field_ids):
        """
        Check if custom fields are properly configured for a project
        
        Args:
            project_key (str): The project key to check
            custom_field_ids (list): List of custom field IDs to check
            
        Returns:
            dict: Dictionary with custom field validation results
        """
        if not self.jira:
            return {"error": "Jira client not initialized"}
            
        results = {}
        
        try:
            # Get create metadata which includes field info
            create_meta = self.jira.issue_createmeta(
                project=project_key,
                expand='projects.issuetypes.fields'
            )
            
            if not create_meta or 'projects' not in create_meta or len(create_meta['projects']) == 0:
                return {"error": f"Could not get metadata for project {project_key}"}
                
            # Get the first issue type's fields
            project_data = create_meta['projects'][0]
            if 'issuetypes' not in project_data or len(project_data['issuetypes']) == 0:
                return {"error": "No issue types found for project"}
                
            # Get fields from the first issue type
            issue_type = project_data['issuetypes'][0]
            fields = issue_type.get('fields', {})
            
            # Check each custom field
            for field_id in custom_field_ids:
                if field_id in fields:
                    field_info = fields[field_id]
                    results[field_id] = {
                        "exists": True,
                        "name": field_info.get('name', 'Unknown'),
                        "required": field_info.get('required', False),
                        "schema": field_info.get('schema', {})
                    }
                else:
                    results[field_id] = {
                        "exists": False
                    }
            
            return results
            
        except Exception as e:
            return {"error": str(e)}

    def get_connection_info(self):
        """
        Get information about the JIRA connection for debugging purposes
        
        Returns:
            dict: Dictionary with connection information
        """
        if not self.jira:
            return {
                "authenticated": False,
                "error": "Jira client not initialized"
            }
            
        try:
            # Test authentication by getting current user
            myself = self.jira.myself()
            
            # Get list of accessible projects
            projects = []
            try:
                # Get first 100 projects (should be enough for most cases)
                project_list = self.jira.get_all_projects(included_archived=False)
                projects = [p.get('key') for p in project_list if 'key' in p]
            except Exception as e:
                projects = ["Error fetching projects: " + str(e)]
            
            # Check permissions for BRUN project specifically
            brun_permissions = {}
            try:
                if 'BRUN' in projects:
                    # Use the correct method to check permissions
                    # First check if we can get the project metadata
                    project_meta = self.jira.get_project(key='BRUN')
                    
                    # Then check if we can get issue creation metadata (confirms we can create issues)
                    create_meta = self.jira.issue_createmeta(
                        project='BRUN',
                        expand='projects.issuetypes.fields'
                    )
                    
                    # Extract available issue types
                    issue_types = []
                    issue_type_details = []
                    if create_meta and 'projects' in create_meta and len(create_meta['projects']) > 0:
                        project_data = create_meta['projects'][0]
                        if 'issuetypes' in project_data:
                            for issue_type in project_data.get('issuetypes', []):
                                name = issue_type.get('name')
                                issue_types.append(name)
                                issue_type_details.append({
                                    'id': issue_type.get('id'),
                                    'name': name,
                                    'description': issue_type.get('description', ''),
                                    'subtask': issue_type.get('subtask', False)
                                })
                    
                    # Check for specific issue type
                    has_story_type = 'Story' in issue_types
                    has_task_type = 'Task' in issue_types
                    has_bug_type = 'Bug' in issue_types
                    
                    # Check if we can get the project's components
                    components = []
                    try:
                        components_data = self.jira.get_project_components('BRUN')
                        components = [c.get('name') for c in components_data if 'name' in c]
                    except Exception as comp_error:
                        components = [f"Error fetching components: {str(comp_error)}"]
                    
                    # Compile permissions info
                    brun_permissions = {
                        "can_access_project": True,
                        "project_lead": project_meta.get('lead', {}).get('displayName') if project_meta else "Unknown",
                        "available_issue_types": issue_types,
                        "issue_type_details": issue_type_details,
                        "has_story_type": has_story_type,
                        "has_task_type": has_task_type,
                        "has_bug_type": has_bug_type,
                        "components": components,
                        "can_create_issues": len(issue_types) > 0
                    }
            except Exception as e:
                brun_permissions = {"error": str(e)}
            
            return {
                "server": self.jira_server,
                "username": myself.get('emailAddress', 'Unknown'),
                "display_name": myself.get('displayName', 'Unknown'),
                "authenticated": True,
                "projects": projects,
                "brun_permissions": brun_permissions
            }
        except Exception as e:
            return {
                "authenticated": False,
                "error": str(e),
                "server": getattr(self, 'jira_server', 'Unknown')
            } 