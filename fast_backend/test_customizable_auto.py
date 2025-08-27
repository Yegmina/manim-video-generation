#!/usr/bin/env python3
"""
Test script for customizable auto mode functionality.

This script demonstrates how to use the new customizable auto mode
with different configurations for retry attempts, model selection, and other parameters.
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
API_BASE = "http://localhost:8000/api/v1"

def test_default_auto_mode():
    """Test the default auto mode behavior (backward compatibility)."""
    print("=== Testing Default Auto Mode ===")
    
    url = f"{API_BASE}/text2video/auto"
    data = {
        "prompt": "Create a simple animation showing a bouncing ball",
        "quality": "LOW_QUALITY",
        "format": "MP4"
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Video ID: {result['id']}")
        print(f"Status: {result['status']}")
        return result['id']
    else:
        print(f"Error: {response.text}")
        return None

def test_customized_auto_mode():
    """Test customized auto mode with specific configuration."""
    print("\n=== Testing Customized Auto Mode ===")
    
    url = f"{API_BASE}/text2video/auto"
    data = {
        "prompt": "Create a complex mathematical animation showing the Pythagorean theorem",
        "quality": "HIGH_QUALITY",
        "format": "MP4",
        "auto_config": {
            "max_total_attempts": 20,
            "max_llm_attempts_per_phase": 5,
            "enable_prompt_rewriting": True,
            "enable_prompt_simplification": True,
            "enable_gemini_fallback": True,
            "enable_video_error_feedback": True,
            "preferred_models": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemma-3-27b-it"],
            "custom_prompt_modifiers": [
                "Use clear mathematical notation",
                "Include step-by-step explanations",
                "Make the animation educational and engaging"
            ]
        }
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Video ID: {result['id']}")
        print(f"Status: {result['status']}")
        print(f"Auto Config: {result.get('metadata', {}).get('auto_config', 'Not found')}")
        return result['id']
    else:
        print(f"Error: {response.text}")
        return None

def test_minimal_auto_mode():
    """Test minimal auto mode with reduced attempts and disabled features."""
    print("\n=== Testing Minimal Auto Mode ===")
    
    url = f"{API_BASE}/text2video/auto"
    data = {
        "prompt": "Show a simple circle animation",
        "quality": "LOW_QUALITY",
        "format": "MP4",
        "auto_config": {
            "max_total_attempts": 5,
            "max_llm_attempts_per_phase": 2,
            "enable_prompt_rewriting": False,
            "enable_prompt_simplification": False,
            "enable_gemini_fallback": False,
            "enable_video_error_feedback": False,
            "preferred_models": ["gemini-2.5-flash"],
            "custom_prompt_modifiers": []
        }
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Video ID: {result['id']}")
        print(f"Status: {result['status']}")
        return result['id']
    else:
        print(f"Error: {response.text}")
        return None

def test_fast_auto_mode():
    """Test fast auto mode optimized for speed."""
    print("\n=== Testing Fast Auto Mode ===")
    
    url = f"{API_BASE}/text2video/auto"
    data = {
        "prompt": "Create a quick text animation",
        "quality": "LOW_QUALITY",
        "format": "MP4",
        "auto_config": {
            "max_total_attempts": 8,
            "max_llm_attempts_per_phase": 2,
            "enable_prompt_rewriting": True,
            "enable_prompt_simplification": True,
            "enable_gemini_fallback": True,
            "enable_video_error_feedback": True,
            "preferred_models": ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
            "custom_prompt_modifiers": [
                "Keep it simple and fast",
                "Use basic animations only"
            ]
        }
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Video ID: {result['id']}")
        print(f"Status: {result['status']}")
        return result['id']
    else:
        print(f"Error: {response.text}")
        return None

def check_video_status(video_id: int):
    """Check the status of a video generation."""
    url = f"{API_BASE}/manim2video/{video_id}/status"
    response = requests.get(url)
    if response.status_code == 200:
        status = response.json()
        print(f"Video {video_id} Status: {status['status']}")
        print(f"Progress: {status['progress']}%")
        if status.get('error_message'):
            print(f"Error: {status['error_message']}")
        return status
    else:
        print(f"Error checking status: {response.text}")
        return None

def main():
    """Run all tests."""
    print("Testing Customizable Auto Mode API")
    print("=" * 50)
    
    # Test different configurations
    video_ids = []
    
    # Test 1: Default auto mode
    video_id = test_default_auto_mode()
    if video_id:
        video_ids.append(video_id)
    
    # Test 2: Customized auto mode
    video_id = test_customized_auto_mode()
    if video_id:
        video_ids.append(video_id)
    
    # Test 3: Minimal auto mode
    video_id = test_minimal_auto_mode()
    if video_id:
        video_ids.append(video_id)
    
    # Test 4: Fast auto mode
    video_id = test_fast_auto_mode()
    if video_id:
        video_ids.append(video_id)
    
    # Check status of all videos
    print("\n" + "=" * 50)
    print("Checking video status...")
    for video_id in video_ids:
        check_video_status(video_id)
        print("-" * 30)

if __name__ == "__main__":
    main()
