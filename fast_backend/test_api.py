"""
Test script for the Manim Video Generation API.

This script demonstrates how to use the API endpoints
to create and manage video generations.
"""

import requests
import json
import time
from pathlib import Path

# API configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_create_video_generation():
    """Test creating a video generation request."""
    print("Testing video generation creation...")
    
    # Sample Manim script
    script_content = '''
from manim import *

class TestAnimation(Scene):
    def construct(self):
        # Create a circle
        circle = Circle(radius=1, color=BLUE, fill_opacity=0.5)
        circle.move_to(ORIGIN)
        
        # Animation sequence
        self.play(Create(circle), run_time=2)
        self.wait(1)
        self.play(circle.animate.scale(2), run_time=2)
        self.wait(1)
        self.play(FadeOut(circle), run_time=1)
'''
    
    # Request data
    data = {
        "title": "Test Circle Animation",
        "description": "A simple test animation with a circle",
        "script_content": script_content,
        "scene_name": "TestAnimation",
        "quality": "low_quality",
        "format": "mp4",
        "output_name": "test_circle",
        "tags": ["test", "circle", "animation"],
        "metadata": {
            "test": True,
            "category": "geometry"
        }
    }
    
    response = requests.post(
        f"{API_BASE}/manim2video/",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        result = response.json()
        print(f"Video generation created: {result['id']}")
        print(f"Status: {result['status']}")
        return result['id']
    else:
        print(f"Error: {response.text}")
        return None

def test_get_video_status(video_id):
    """Test getting video generation status."""
    print(f"Testing status check for video {video_id}...")
    
    response = requests.get(f"{API_BASE}/manim2video/{video_id}/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Video status: {result['status']}")
        print(f"Progress: {result['progress']}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def test_list_video_generations():
    """Test listing video generations."""
    print("Testing video generations list...")
    
    response = requests.get(f"{API_BASE}/manim2video/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Total videos: {result['total']}")
        print(f"Items: {len(result['items'])}")
        return result['items']
    else:
        print(f"Error: {response.text}")
        return []

def test_download_video(video_id):
    """Test downloading a completed video."""
    print(f"Testing video download for {video_id}...")
    
    response = requests.get(f"{API_BASE}/manim2video/{video_id}/download")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        # Save the video file
        filename = f"downloaded_video_{video_id}.mp4"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Video downloaded: {filename}")
        return filename
    else:
        print(f"Error: {response.text}")
        return None

def test_statistics():
    """Test getting statistics."""
    print("Testing statistics...")
    
    response = requests.get(f"{API_BASE}/manim2video/statistics/summary")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Statistics: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Main test function."""
    print("=== Manim Video Generation API Test ===")
    print()
    
    # Test health check
    test_health_check()
    
    # Test creating video generation
    video_id = test_create_video_generation()
    
    if video_id:
        print(f"Created video generation with ID: {video_id}")
        print()
        
        # Wait a bit for processing to start
        print("Waiting for video generation to start...")
        time.sleep(2)
        
        # Test status check
        status_info = test_get_video_status(video_id)
        print()
        
        # Test listing videos
        videos = test_list_video_generations()
        print()
        
        # Test statistics
        stats = test_statistics()
        print()
        
        # Wait for completion and test download
        print("Waiting for video generation to complete...")
        max_wait = 60  # Maximum wait time in seconds
        wait_time = 0
        
        while wait_time < max_wait:
            status_info = test_get_video_status(video_id)
            if status_info and status_info['status'] == 'completed':
                print("Video generation completed!")
                break
            elif status_info and status_info['status'] in ['failed', 'timeout']:
                print("Video generation failed!")
                break
            
            time.sleep(5)
            wait_time += 5
            print(f"Waited {wait_time} seconds...")
        
        # Try to download the video
        if status_info and status_info['status'] == 'completed':
            test_download_video(video_id)
    
    print()
    print("=== Test completed ===")

if __name__ == "__main__":
    main()
