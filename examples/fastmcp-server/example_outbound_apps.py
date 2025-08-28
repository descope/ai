#!/usr/bin/env python3
"""
Example script demonstrating Descope Outbound App Management functions.
This script shows how to use the new outbound app features from the Python SDK.
"""

import os
from dotenv import load_dotenv
from descope import DescopeClient
from descope.management import Management

load_dotenv()

def main():
    # Get configuration from environment
    project_id = os.getenv("DESCOPE_PROJECT_ID")
    base_url = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com")
    management_key = os.getenv("DESCOPE_MANAGEMENT_KEY")
    
    if not project_id:
        print("Error: DESCOPE_PROJECT_ID environment variable must be set")
        return
    
    if not management_key:
        print("Error: DESCOPE_MANAGEMENT_KEY environment variable must be set")
        return
    
    # Initialize clients
    descope_client = DescopeClient(project_id=project_id, base_url=base_url)
    descope_mgmt = Management(project_id=project_id, management_key=management_key, base_url=base_url)
    
    print("=== Descope Outbound App Management Example ===\n")
    
    try:
        # 1. List all outbound applications
        print("1. Listing all outbound applications...")
        outbound_apps = descope_mgmt.outbound_application.list()
        
        if not outbound_apps:
            print("No outbound applications found.")
            
            # 2. Create a new outbound application
            print("\n2. Creating a new outbound application...")
            new_app = descope_mgmt.outbound_application.create(
                name="Example Outbound App",
                description="An example outbound application created via Python SDK"
            )
            print(f"Created app with ID: {new_app.get('id')}")
            app_id = new_app.get('id')
        else:
            print(f"Found {len(outbound_apps)} outbound application(s):")
            for app in outbound_apps:
                print(f"  - {app.get('name')} (ID: {app.get('id')})")
            app_id = outbound_apps[0].get('id')  # Use the first app for examples
        
        # 3. Get details of a specific application
        print(f"\n3. Getting details for application {app_id}...")
        app_details = descope_mgmt.outbound_application.get(app_id)
        print(f"App Name: {app_details.get('name')}")
        print(f"Description: {app_details.get('description')}")
        print(f"Status: {app_details.get('status')}")
        
        # 4. Get an outbound token for the application
        print(f"\n4. Getting outbound token for application {app_id}...")
        token_response = descope_mgmt.outbound_application.get_token(app_id)
        print(f"Token: {token_response.get('token', 'N/A')[:50]}...")
        print(f"Expires: {token_response.get('expires', 'N/A')}")
        
        # 5. Example: Get user token (requires a valid user ID)
        print("\n5. Example: Getting user token...")
        print("Note: This requires a valid user ID. Replace 'example_user_id' with a real user ID.")
        try:
            # This will likely fail unless you have a real user ID
            user_token = descope_mgmt.outbound_application.get_user_token("example_user_id")
            print(f"User Token: {user_token.get('token', 'N/A')[:50]}...")
        except Exception as e:
            print(f"User token example failed (expected): {str(e)}")
        
        # 6. Example: Get tenant token (requires a valid tenant ID)
        print("\n6. Example: Getting tenant token...")
        print("Note: This requires a valid tenant ID. Replace 'example_tenant_id' with a real tenant ID.")
        try:
            # This will likely fail unless you have a real tenant ID
            tenant_token = descope_mgmt.outbound_application.get_tenant_token("example_tenant_id")
            print(f"Tenant Token: {tenant_token.get('token', 'N/A')[:50]}...")
        except Exception as e:
            print(f"Tenant token example failed (expected): {str(e)}")
        
        print("\n=== Example completed successfully! ===")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure you have:")
        print("1. A valid DESCOPE_PROJECT_ID")
        print("2. A valid DESCOPE_MANAGEMENT_KEY with appropriate permissions")
        print("3. Outbound apps feature enabled in your Descope project")

if __name__ == "__main__":
    main() 