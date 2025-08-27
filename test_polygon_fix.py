#!/usr/bin/env python3
"""
Test script for the Polygon coordinate fix.
"""

import sys
import os

# Set up environment variables BEFORE importing any modules
os.environ["GOOGLE_API_KEY"] = "AIzaSyCBPyjQeYKfzOuhuh6xBDbjjaWWNXpX1C0"
os.environ["DATABASE_URL"] = "sqlite:///./manim_video.db"
os.environ["SECRET_KEY"] = "test"
os.environ["DEBUG"] = "True"

# Add the fast_backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fast_backend'))

from app.services.manim_code_converter import convert_manim_code

def test_polygon_coordinate_fix():
    """Test the Polygon coordinate fix."""
    
    # Test case 1: Simple 2D coordinates
    original_code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Car
        car_body = Polygon(
            [-1, -0.5], [1, -0.5], [1.5, 0.5], [-1.5, 0.5],
            stroke_width=0,
            fill_opacity=1,
            color=BLUE
        )
        
        self.play(Create(car_body))
        self.wait(1)
"""
    
    print("Testing Polygon coordinate fix...")
    print("Original code:")
    print(original_code)
    print("-" * 50)
    
    converted_code = convert_manim_code(original_code)
    
    print("Converted code:")
    print(converted_code)
    print("-" * 50)
    
    # Check if the fix was applied
    if "[-1, -0.5, 0]" in converted_code and "[1, -0.5, 0]" in converted_code:
        print("✅ Polygon coordinate fix applied successfully!")
        return True
    else:
        print("❌ Polygon coordinate fix failed!")
        return False

def test_compilation():
    """Test if the converted code can be compiled."""
    
    original_code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        car_body = Polygon(
            [-1, -0.5], [1, -0.5], [1.5, 0.5], [-1.5, 0.5],
            stroke_width=0,
            fill_opacity=1,
            color=BLUE
        )
        
        self.play(Create(car_body))
        self.wait(1)
"""
    
    converted_code = convert_manim_code(original_code)
    
    try:
        # Try to compile the converted code
        compile(converted_code, '<string>', 'exec')
        print("✅ Converted code compiles successfully!")
        return True
    except Exception as e:
        print(f"❌ Converted code compilation failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing Polygon coordinate fix...")
    print()
    
    # Test 1: Coordinate conversion
    success1 = test_polygon_coordinate_fix()
    
    # Test 2: Compilation
    success2 = test_compilation()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    print(f"Coordinate conversion: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Code compilation: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The Polygon coordinate fix is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
    
    return success1 and success2

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
