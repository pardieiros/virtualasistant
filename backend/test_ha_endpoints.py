#!/usr/bin/env python
"""Script to list and test Home Assistant API endpoints."""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from assistant.models import HomeAssistantConfig
import requests

def get_headers(config):
    """Get authentication headers."""
    return {
        'Authorization': f'Bearer {config.long_lived_token}',
        'Content-Type': 'application/json',
    }

def test_endpoint(name, method, url, headers, data=None, description=""):
    """Test an API endpoint and return the result."""
    print(f"\n{'='*70}")
    print(f"📋 {name}")
    print(f"{'='*70}")
    if description:
        print(f"📝 {description}")
    print(f"🔗 {method} {url}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            print(f"   ⚠ Unsupported method: {method}")
            return None
        
        response.raise_for_status()
        result = response.json() if response.content else {}
        
        print(f"   ✅ Status: {response.status_code}")
        
        # Format output based on endpoint type
        if isinstance(result, list):
            print(f"   📊 Items returned: {len(result)}")
            if result and len(result) > 0:
                if isinstance(result[0], dict) and 'entity_id' in result[0]:
                    # States list
                    print(f"   📋 Sample entities (first 5):")
                    for item in result[:5]:
                        entity_id = item.get('entity_id', 'unknown')
                        state = item.get('state', 'unknown')
                        print(f"      • {entity_id}: {state}")
                elif isinstance(result[0], dict) and 'domain' in result[0]:
                    # Services list
                    print(f"   📋 Sample services (first 5):")
                    for item in result[:5]:
                        domain = item.get('domain', 'unknown')
                        services = item.get('services', {})
                        print(f"      • {domain}: {len(services)} services")
                else:
                    print(f"   📋 Sample items (first 3):")
                    for item in result[:3]:
                        print(f"      • {json.dumps(item, indent=8)[:200]}")
        elif isinstance(result, dict):
            if 'message' in result:
                print(f"   💬 Message: {result['message']}")
            if 'location_name' in result:
                print(f"   📍 Location: {result.get('location_name')}")
                print(f"   🌍 Timezone: {result.get('time_zone')}")
                print(f"   🏠 Version: {result.get('version')}")
            if 'entity_id' in result:
                print(f"   🏷️  Entity: {result.get('entity_id')}")
                print(f"   📊 State: {result.get('state')}")
                print(f"   📝 Attributes: {len(result.get('attributes', {}))} attributes")
            if 'services' in result:
                print(f"   📋 Domains: {len(result.get('services', {}))}")
                for domain, services in list(result.get('services', {}).items())[:5]:
                    print(f"      • {domain}: {len(services)} services")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   📊 Status: {e.response.status_code}")
            try:
                error_data = e.response.json()
                print(f"   📝 Error details: {json.dumps(error_data, indent=6)}")
            except:
                print(f"   📝 Response: {e.response.text[:200]}")
        return None

def main():
    # Get user 1
    try:
        user = User.objects.get(id=1)
        print(f"👤 User: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("❌ User with ID 1 not found!")
        return
    
    # Check config
    config = HomeAssistantConfig.objects.filter(user=user, enabled=True).first()
    
    if not config or not config.base_url or not config.long_lived_token:
        print("❌ Home Assistant not configured or not enabled!")
        return
    
    base_url = config.base_url.rstrip('/')
    headers = get_headers(config)
    
    print("\n" + "="*70)
    print("🏠 HOME ASSISTANT API ENDPOINTS TEST")
    print("="*70)
    print(f"🌐 Base URL: {base_url}")
    
    # List of endpoints to test
    endpoints = [
        {
            'name': 'API Status',
            'method': 'GET',
            'url': f'{base_url}/api/',
            'description': 'Check if API is running and accessible',
        },
        {
            'name': 'Configuration Info',
            'method': 'GET',
            'url': f'{base_url}/api/config',
            'description': 'Get Home Assistant configuration information (location, version, etc.)',
        },
        {
            'name': 'All States',
            'method': 'GET',
            'url': f'{base_url}/api/states',
            'description': 'Get current state of all entities (lights, switches, sensors, etc.)',
        },
        {
            'name': 'All Services',
            'method': 'GET',
            'url': f'{base_url}/api/services',
            'description': 'List all available services (turn_on, turn_off, etc.) organized by domain',
        },
        {
            'name': 'All Components',
            'method': 'GET',
            'url': f'{base_url}/api/components',
            'description': 'List all loaded components/integrations',
        },
        {
            'name': 'All Events',
            'method': 'GET',
            'url': f'{base_url}/api/events',
            'description': 'List all available event types',
        },
        {
            'name': 'History (Last Hour)',
            'method': 'GET',
            'url': f'{base_url}/api/history/period',
            'description': 'Get historical states (requires timestamp parameters)',
        },
    ]
    
    results = {}
    for endpoint in endpoints:
        result = test_endpoint(
            endpoint['name'],
            endpoint['method'],
            endpoint['url'],
            headers,
            endpoint.get('data'),
            endpoint.get('description', '')
        )
        results[endpoint['name']] = result
    
    # Get a sample entity to test entity-specific endpoints
    if results.get('All States') and len(results['All States']) > 0:
        sample_entity = results['All States'][0]
        entity_id = sample_entity.get('entity_id')
        
        if entity_id:
            print(f"\n{'='*70}")
            print(f"🔍 TESTING ENTITY-SPECIFIC ENDPOINTS")
            print(f"{'='*70}")
            print(f"📌 Using sample entity: {entity_id}")
            
            entity_endpoints = [
                {
                    'name': f'Get State: {entity_id}',
                    'method': 'GET',
                    'url': f'{base_url}/api/states/{entity_id}',
                    'description': f'Get current state and attributes of {entity_id}',
                },
            ]
            
            for endpoint in entity_endpoints:
                result = test_endpoint(
                    endpoint['name'],
                    endpoint['method'],
                    endpoint['url'],
                    headers,
                    endpoint.get('data'),
                    endpoint.get('description', '')
                )
                results[endpoint['name']] = result
    
    # Test service call examples
    if results.get('All Services'):
        print(f"\n{'='*70}")
        print(f"⚙️  SERVICE CALL EXAMPLES")
        print(f"{'='*70}")
        print("💡 These are examples - modify entity_id and parameters as needed")
        
        service_examples = [
            {
                'name': 'Check Config',
                'domain': 'homeassistant',
                'service': 'check_config',
                'data': {},
                'description': 'Check Home Assistant configuration for errors',
            },
            {
                'name': 'Reload Config',
                'domain': 'homeassistant',
                'service': 'reload_config_entry',
                'data': {'entry_id': 'example'},  # This will likely fail, but shows the format
                'description': 'Reload a configuration entry (example - will likely fail)',
            },
        ]
        
        for example in service_examples:
            url = f'{base_url}/api/services/{example["domain"]}/{example["service"]}'
            result = test_endpoint(
                f'Service: {example["domain"]}.{example["service"]}',
                'POST',
                url,
                headers,
                example['data'],
                example['description']
            )
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    successful = sum(1 for r in results.values() if r is not None)
    total = len(results)
    print(f"✅ Successful: {successful}/{total}")
    print(f"\n📚 Available Actions:")
    print(f"   • Monitor entity states (lights, switches, sensors)")
    print(f"   • Control devices (turn on/off lights, set temperature, etc.)")
    print(f"   • Get historical data")
    print(f"   • Trigger automations via events")
    print(f"   • Check system status and configuration")
    print(f"   • List all available services and components")
    print(f"\n💡 To call services, use: POST /api/services/<domain>/<service>")
    print(f"   Example: POST /api/services/light/turn_on")
    print(f"   Body: {{'entity_id': 'light.living_room'}}")
    print(f"\n{'='*70}")

if __name__ == '__main__':
    main()



