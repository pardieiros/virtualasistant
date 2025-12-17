#!/usr/bin/env python
"""Script to check Home Assistant config for user 1 and test the API."""
import os
import sys
import django

# Setup Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from assistant.models import HomeAssistantConfig
from assistant.services.homeassistant_client import call_homeassistant_service
import requests

def main():
    # Get user 1
    try:
        user = User.objects.get(id=1)
        print(f"✓ User found: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("✗ User with ID 1 not found!")
        return
    
    # Check config
    config = HomeAssistantConfig.objects.filter(user=user).first()
    
    if not config:
        print("\n✗ No Home Assistant configuration found for this user.")
        print("  You need to create a configuration first.")
        return
    
    print(f"\n✓ Configuration found:")
    print(f"  - Base URL: {config.base_url or '(not set)'}")
    print(f"  - Token: {'✓ Set' if config.long_lived_token else '✗ Not set'}")
    print(f"  - Enabled: {config.enabled}")
    
    if not config.enabled:
        print("\n⚠ Configuration exists but is not enabled.")
        return
    
    if not config.base_url or not config.long_lived_token:
        print("\n⚠ Configuration is incomplete (missing base_url or token).")
        return
    
    # Test API connection
    print("\n" + "="*60)
    print("Testing Home Assistant API...")
    print("="*60)
    
    # Test 1: Get Home Assistant info
    try:
        url = f"{config.base_url.rstrip('/')}/api/"
        headers = {
            'Authorization': f'Bearer {config.long_lived_token}',
            'Content-Type': 'application/json',
        }
        
        print(f"\n1. Testing connection to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"   ✓ Connection successful!")
        print(f"   Response: {data}")
        
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Connection failed: {str(e)}")
        return
    
    # Test 2: Get states
    try:
        url = f"{config.base_url.rstrip('/')}/api/states"
        print(f"\n2. Getting all states from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        states = response.json()
        print(f"   ✓ Retrieved {len(states)} states")
        if states:
            print(f"   Sample states:")
            for state in states[:5]:
                print(f"     - {state.get('entity_id')}: {state.get('state')}")
            if len(states) > 5:
                print(f"     ... and {len(states) - 5} more")
        
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Failed to get states: {str(e)}")
    
    # Test 3: Test service call function
    print(f"\n3. Testing service call function...")
    result = call_homeassistant_service(user, 'homeassistant', 'check_config')
    print(f"   Result: {result}")
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

if __name__ == '__main__':
    main()

