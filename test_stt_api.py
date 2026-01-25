#!/usr/bin/env python3
"""
Test script for STT API integration.
Tests if the STT API is accessible and responding correctly.
"""
import requests
import os
import sys

STT_API_URL = os.getenv('STT_API_URL', 'http://192.168.1.68:8008')

def test_stt_api_connection():
    """Test if STT API is accessible."""
    print(f"Testing STT API connection to: {STT_API_URL}")
    
    # Test 1: Check if API is reachable
    try:
        # Try a simple GET request to see if server is up
        response = requests.get(f"{STT_API_URL}/", timeout=5)
        print(f"✓ API server is reachable (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to STT API at {STT_API_URL}")
        print("  Make sure the STT API server is running and accessible")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ Connection to STT API timed out")
        return False
    except Exception as e:
        print(f"⚠ API server responded but may not be the STT endpoint: {e}")
    
    # Test 2: Try to transcribe with a minimal audio file
    # Create a minimal WebM file (just header, no actual audio)
    # This is a very basic WebM container header
    minimal_webm = bytes([
        0x1A, 0x45, 0xDF, 0xA3, 0x9F, 0x42, 0x86, 0x81,  # EBML header
        0x01, 0x42, 0xF2, 0x81, 0x01, 0x42, 0xF3, 0x81,
        0x01, 0x42, 0xF7, 0x81, 0x04, 0x42, 0x82, 0x84,
        0x77, 0x65, 0x62, 0x6D, 0x42, 0x87, 0x81, 0x04,
        0x42, 0x85, 0x81, 0x02
    ])
    
    print(f"\nTesting transcription endpoint: {STT_API_URL}/stt/transcribe")
    try:
        files = {
            'file': ('test_audio.webm', minimal_webm, 'audio/webm')
        }
        params = {
            'language': 'pt'
        }
        
        response = requests.post(
            f"{STT_API_URL}/stt/transcribe",
            files=files,
            params=params,
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✓ Transcription endpoint is working!")
                print(f"  Response: {result}")
                return True
            except ValueError:
                print(f"⚠ Got 200 but response is not JSON: {response.text[:200]}")
                return True  # Still consider it working if we get 200
        else:
            print(f"✗ Transcription endpoint returned error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error calling transcription endpoint: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_stt_api_connection()
    sys.exit(0 if success else 1)

