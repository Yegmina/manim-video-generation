"""
Simple Manim Test Script

This script tests basic Manim functionality without generating videos
to avoid system resource issues.
"""

import sys
import os

def test_manim_import():
    """Test if Manim can be imported successfully."""
    try:
        import manim
        print(f"✓ Manim imported successfully")
        print(f"  Version: {manim.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Failed to import Manim: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error importing Manim: {e}")
        return False

def test_manim_basic_objects():
    """Test if basic Manim objects can be created."""
    try:
        from manim import Scene, Circle, Square, Text
        print("✓ Basic Manim objects imported successfully")
        
        # Test creating objects (without rendering)
        circle = Circle()
        square = Square()
        text = Text("Test")
        
        print("✓ Basic Manim objects created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create basic Manim objects: {e}")
        return False

def test_manim_command():
    """Test if Manim command is accessible."""
    import subprocess
    
    try:
        # Test with Python module approach
        result = subprocess.run(
            ["py", "-m", "manim", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Manim command accessible via Python module")
            return True
        else:
            print(f"✗ Manim command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Failed to test Manim command: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Manim Installation Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_manim_import),
        ("Basic Objects Test", test_manim_basic_objects),
        ("Command Test", test_manim_command)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print(f"\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Manim is properly installed.")
        print("\nTo resolve the paging file issue:")
        print("1. Open System Properties (Win + Pause/Break)")
        print("2. Click 'Advanced system settings'")
        print("3. Click 'Settings' under Performance")
        print("4. Click 'Advanced' tab")
        print("5. Click 'Change' under Virtual memory")
        print("6. Increase the paging file size (recommend 8GB or more)")
        print("7. Restart your computer")
    else:
        print("✗ Some tests failed. Please check your Manim installation.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()



