import streamlit as st
from utils.jira_service import JiraService

def validate_issue_type_for_project(project_key, issue_type):
    """
    Validate if an issue type is available for a specific project
    
    Args:
        project_key (str): The project key to check
        issue_type (str): The issue type to validate
        
    Returns:
        tuple: (is_valid, available_types, error_message)
            - is_valid (bool): True if issue type is valid, False otherwise
            - available_types (list): List of available issue types
            - error_message (str): Error message if any
    """
    try:
        jira_service = JiraService()
        connection_info = jira_service.get_connection_info()
        
        # Check if authenticated
        if not connection_info.get("authenticated", False):
            return False, [], f"Authentication failed: {connection_info.get('error', 'Unknown error')}"
        
        # Check if project exists
        projects = connection_info.get("projects", [])
        if project_key not in projects:
            return False, [], f"Project {project_key} not found in accessible projects"
        
        # Get project permissions
        project_permissions = connection_info.get(f"{project_key.lower()}_permissions", {})
        if not isinstance(project_permissions, dict) or not project_permissions:
            return False, [], f"Could not retrieve permissions for {project_key}"
        
        # Get available issue types
        available_types = project_permissions.get("available_issue_types", [])
        if not available_types:
            return False, [], f"No issue types available for {project_key}"
        
        # Check if issue type is available
        is_valid = issue_type in available_types
        error_message = "" if is_valid else f"Issue type '{issue_type}' not found in available types"
        
        return is_valid, available_types, error_message
        
    except Exception as e:
        return False, [], f"Error validating issue type: {str(e)}"


def debug_jira_connection(project_key=None, issue_type=None, custom_field_ids=None, jira_service=None):
    """
    Debug JIRA connection and display detailed information about the connection status
    
    Args:
        project_key (str): The project key to check permissions for (default: "BRUN")
        issue_type (str, optional): The issue type to validate against the project (default: None)
        custom_field_ids (list, optional): List of custom field IDs to check
        jira_service (JiraService, optional): Existing JiraService instance to use (default: None)
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    st.write(f"### Testing JIRA Connection for {project_key}...")
    
    if issue_type:
        st.write(f"Validating issue type: '{issue_type}'")
    
    try:
        # Use provided jira_service or create a new one
        if jira_service is None:
            jira_service = JiraService()
        connection_info = jira_service.get_connection_info()
        
        # Display connection status
        if connection_info.get("authenticated", False):
            st.success(f"✅ Successfully authenticated as {connection_info.get('display_name', 'Unknown')}")
            is_connected = True
        else:
            st.error(f"❌ Authentication failed: {connection_info.get('error', 'Unknown error')}")
            is_connected = False
        
        # Display project access
        projects = connection_info.get("projects", [])
        if isinstance(projects, list) and len(projects) > 0:
            st.success(f"✅ Access to {len(projects)} projects")
            
            # Check for specific project
            if project_key in projects:
                st.success(f"✅ Has access to {project_key} project")
                
                # Check permissions
                project_permissions = connection_info.get(f"{project_key.lower()}_permissions", {})
                if isinstance(project_permissions, dict) and project_permissions:
                    st.write(f"#### {project_key} Project Permissions:")
                    
                    # Check if we can create issues
                    if project_permissions.get("can_create_issues", False):
                        st.success(f"✅ Can create issues in {project_key} project")
                    else:
                        st.error(f"❌ Cannot create issues in {project_key} project")
                    
                    # Check issue types
                    issue_types = project_permissions.get("available_issue_types", [])
                    if issue_types:
                        st.success(f"✅ Available issue types: {', '.join(issue_types)}")
                        
                        # Validate specific issue type if provided
                        if issue_type:
                            if issue_type in issue_types:
                                st.success(f"✅ Specified issue type '{issue_type}' is available in {project_key} project")
                            else:
                                st.error(f"❌ Specified issue type '{issue_type}' is NOT available in {project_key} project")
                                st.warning(f"⚠️ Available issue types: {', '.join(issue_types)}")
                        
                        # Check for common issue types
                        common_types = {"Story": "has_story_type", "Task": "has_task_type", "Bug": "has_bug_type"}
                        for type_name, type_flag in common_types.items():
                            if project_permissions.get(type_flag, False):
                                st.success(f"✅ '{type_name}' issue type is available")
                    else:
                        st.error("❌ No issue types available")
                    
                    # Check components
                    components = project_permissions.get("components", [])
                    if "Billing" in components:
                        st.success("✅ 'Billing' component is available")
                else:
                    st.warning(f"⚠️ Could not retrieve {project_key} permissions")
                
                # Check custom fields
                st.write("#### Custom Fields Check:")
                try:
                    custom_fields = jira_service.check_custom_fields(
                        project_key, 
                        custom_field_ids
                    )
                    
                    if "error" in custom_fields:
                        st.error(f"❌ Error checking custom fields: {custom_fields['error']}")
                    else:
                        for field_id, field_info in custom_fields.items():
                            if field_info.get("exists", False):
                                st.success(f"✅ {field_id} ({field_info.get('name', 'Unknown')}) exists")
                                if field_info.get("required", False):
                                    st.warning(f"⚠️ {field_id} is required")
                            else:
                                st.error(f"❌ {field_id} does NOT exist in {project_key} project")
                except Exception as cf_error:
                    st.error(f"❌ Error checking custom fields: {str(cf_error)}")
                    
            else:
                st.error(f"❌ No access to {project_key} project")
                st.write("Available projects (first 10):")
                st.write(", ".join(projects[:10]))
                if len(projects) > 10:
                    st.write(f"...and {len(projects) - 10} more")
        else:
            st.error("❌ No projects accessible")
        
        return is_connected
        
    except Exception as e:
        st.error(f"Error testing JIRA connection: {str(e)}")
        return False


def try_create_jira_ticket(jira_service, ticket_params, issue_types=None):
    """
    Try to create a JIRA ticket with different issue types using a for loop
    
    Args:
        jira_service: An instance of JiraService
        ticket_params (dict): Parameters for ticket creation
            - project_key (str): The JIRA project key
            - summary (str): Ticket summary
            - description (str): Ticket description
            - labels (list): List of labels to apply
            - Any additional parameters needed for ticket creation
        issue_types (list, optional): List of issue types to try (default: ["Story", "Task", "Bug"])
    
    Returns:
        tuple: (ticket_url, error_messages)
            - ticket_url (str): URL of the created ticket or None if creation failed
            - error_messages (list): List of error messages for each failed attempt
    """
    # Default issue types if none provided
    if issue_types is None:
        issue_types = ["Story", "Task", "Bug"]
    
    ticket_url = None
    error_messages = []
    
    # Try each issue type in a loop
    for issue_type in issue_types:
        try:
            # Create a copy of ticket params with the current issue type
            params = dict(ticket_params)
            params["issue_type"] = issue_type
            
            # Attempt to create the ticket with current issue type
            ticket_url = jira_service.create_ticket(**params)
            
            # If successful, break out of the loop
            if ticket_url:
                break
                
        except Exception as e:
            # Collect error message and continue to next issue type
            error_messages.append(f"Failed with '{issue_type}' type: {str(e)}")
    
    return ticket_url, error_messages


def run_test_ticket_creation(jira_service, project_key, project_permissions, custom_field_ids=None):
    """
    Run test ticket creation with different configurations
    
    Args:
        jira_service: The JiraService instance
        project_key (str): The project key to create tickets in
        project_permissions (dict): Project permissions information
        custom_field_ids (list, optional): List of custom field IDs to check and test
    """
    st.write("Attempting to create a test ticket...")
    
    # Get available issue types
    available_types = project_permissions.get("available_issue_types", [])
    first_type = available_types[0] if available_types else "Task"  # Default to Task if no types available
    second_type = available_types[1] if len(available_types) > 1 else first_type
    
    # Helper function to validate issue type
    def validate_issue_type(issue_type, project):
        if not available_types:
            st.warning(f"⚠️ No issue types available for {project} project. Using '{issue_type}' anyway.")
            return True
        
        if issue_type in available_types:
            st.success(f"✅ Issue type '{issue_type}' is valid for {project} project")
            return True
        else:
            st.error(f"❌ Issue type '{issue_type}' is NOT valid for {project} project")
            st.warning(f"⚠️ Available types: {', '.join(available_types)}")
            return False
    
    # Helper function to create a ticket and record results
    def create_and_record_ticket(issue_type, test_name, extra_params=None, skip_condition=False):
        if skip_condition or not validate_issue_type(issue_type, project_key):
            return (f"{test_name}", "Skipped - Invalid Issue Type or Condition Not Met", None)
        
        ticket_params = {
            "project_key": project_key,
            "summary": f"TEST {issue_type.upper()} {test_name.upper()} - Please Delete",
            "description": f"This is a test ticket using {issue_type} type with {test_name.lower()} to verify API permissions. Please delete.",
            "issue_type": issue_type
        }
        
        # Add any extra parameters
        if extra_params:
            ticket_params.update(extra_params)
        
        try:
            result = jira_service.create_ticket(**ticket_params)
            if result:
                st.success(f"✅ Successfully created {test_name}: [View]({result})")
                return (f"{test_name}", "Success", result)
            else:
                st.error(f"❌ Failed to create {test_name}")
                return (f"{test_name}", "Failed", None)
        except Exception as e:
            st.error(f"❌ Error creating {test_name}: {str(e)}")
            return (f"{test_name}", "Error", str(e))

    # Define test cases with their parameters
    test_cases = [
        {
            "name": f"Basic {first_type}",
            "issue_type": first_type,
            "extra_params": {}
        },
        {
            "name": f"{second_type} with Labels",
            "issue_type": second_type,
            "extra_params": {"labels": ["test", "automated_jira_ticket"]}
        },
        {
            "name": f"{first_type} with Components",
            "issue_type": first_type,
            "extra_params": {"components": ["Billing"]}
        }
    ]
    
    # Add custom fields test case if custom field IDs are provided
    if custom_field_ids:
        custom_fields_kwargs = {}
        for i, field_id in enumerate(custom_field_ids):
            # Assign test values based on field index
            custom_fields_kwargs[field_id] = ["Test Vendor"] if i == 0 else i
        
        test_cases.append({
            "name": f"{first_type} with Custom Fields",
            "issue_type": first_type,
            "extra_params": custom_fields_kwargs,
            "skip_condition": not custom_field_ids
        })
    
    # Run all test cases and collect results
    test_results = []
    for test_case in test_cases:
        skip_condition = test_case.get("skip_condition", False)
        result = create_and_record_ticket(
            test_case["issue_type"],
            test_case["name"],
            test_case["extra_params"],
            skip_condition
        )
        test_results.append(result)
    
    # Summary
    st.write("#### Test Results Summary:")
    for test, status, details in test_results:
        if status == "Success":
            st.success(f"✅ {test}: Success")
        elif status == "Failed":
            st.error(f"❌ {test}: Failed")
        elif status.startswith("Skipped"):
            st.warning(f"⚠️ {test}: {status}")
        else:
            st.error(f"❌ {test}: Error - {details}")
    
    # Final recommendation
    successes = [t for t, s, _ in test_results if s == "Success"]
    if successes:
        successful_features = [s.split(' with ')[1] for s in successes if ' with ' in s]
        st.info(f"""
        **Recommendation:** Use the following configuration for your tickets in {project_key} project:
        - Issue Type: {successes[0].split(' ')[0]}
        - Include: {', '.join(successful_features) if successful_features else "Basic ticket only"}
        """)
    else:
        st.error(f"""
        **All tests failed.** Please check:
        1. The API user's permissions in JIRA
        2. The project key '{project_key}' is correct
        3. The JIRA instance is accessible
        4. The issue types are valid for this project
        """) 