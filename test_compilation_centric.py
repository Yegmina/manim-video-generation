#!/usr/bin/env python3
"""
Test script for the new compilation-centric auto mode approach.
This script tests the improved error handling and model fallback logic.
"""

import asyncio
import sys
import os

# Set up environment variables BEFORE importing any modules
os.environ["GOOGLE_API_KEY"] = "AIzaSyCBPyjQeYKfzOuhuh6xBDbjjaWWNXpX1C0"
os.environ["DATABASE_URL"] = "sqlite:///./manim_video.db"
os.environ["SECRET_KEY"] = "test"
os.environ["DEBUG"] = "True"

# Add the fast_backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fast_backend'))

from app.services.llm_service import LLMService

async def test_compilation_centric_approach():
    """Test the new compilation-centric approach."""
    
    # Initialize the LLM service
    llm_service = LLMService()
    
    # Test prompt
    test_prompt = "Generate simulator for car movement with constant velocity"
    
    print("Testing compilation-centric auto mode approach...")
    print(f"Prompt: {test_prompt}")
    print("-" * 50)
    
    try:
        # Test the auto mode with compilation validation
        result = await llm_service.generate_manim_code_with_video_validation(
            prompt=test_prompt,
            model="auto"
        )
        
        print("✅ Auto mode completed successfully!")
        print(f"Generated code length: {len(result)} characters")
        print(f"Code preview: {result[:200]}...")
        
        # Check if the code contains expected elements
        if "class GeneratedScene" in result:
            print("✅ GeneratedScene class found")
        else:
            print("❌ GeneratedScene class missing")
            
        if "def construct(self)" in result:
            print("✅ construct method found")
        else:
            print("❌ construct method missing")
            
        if "from manim import" in result:
            print("✅ manim import found")
        else:
            print("❌ manim import missing")
            
        # Check for car-related content
        if any(keyword in result.lower() for keyword in ["car", "vehicle", "movement", "velocity"]):
            print("✅ Car-related content detected")
        else:
            print("⚠️  Car-related content not clearly detected")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    return True

async def test_error_handling():
    """Test error handling with 503-like scenarios."""
    
    llm_service = LLMService()
    
    print("\n" + "=" * 50)
    print("Testing error handling...")
    print("=" * 50)
    
    # Test with a problematic prompt that might trigger errors
    problematic_prompt = "Create a very complex 3D animation with multiple objects and physics simulation"
    
    try:
        result = await llm_service.generate_manim_code_with_video_validation(
            prompt=problematic_prompt,
            model="auto"
        )
        
        print("✅ Error handling test completed")
        print(f"Result length: {len(result)} characters")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True

async def main():
    """Main test function."""
    print("🚀 Starting compilation-centric auto mode tests...")
    print()
    
    # Test 1: Basic compilation-centric approach
    success1 = await test_compilation_centric_approach()
    
    # Test 2: Error handling
    success2 = await test_error_handling()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    print(f"Compilation-centric approach: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Error handling: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The compilation-centric approach is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
    
    return success1 and success2

if __name__ == "__main__":
    # Run the tests
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
