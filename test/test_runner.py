"""
Test Runner for Manim Video Generation

This script demonstrates how to use the ManimVideoGenerator class
to create videos from various example scripts.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import the video generator
sys.path.append(str(Path(__file__).parent.parent))

from manim_video_generator import ManimVideoGenerator, generate_manim_video


def test_basic_animations():
    """
    Test basic circle and text animations.
    
    This function demonstrates how to generate videos from
    basic animation scripts with different quality settings.
    """
    print("Testing basic animations...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Test basic circle animation
    circle_video = generator.generate_video(
        script_path="test/basic_circle_animation.py",
        scene_name="BasicCircleAnimation",
        quality="low_quality",
        output_name="basic_circle"
    )
    
    if circle_video:
        print(f"✓ Basic circle animation generated: {circle_video}")
    else:
        print("✗ Basic circle animation failed")
    
    # Test circle with text
    text_video = generator.generate_video(
        script_path="test/basic_circle_animation.py",
        scene_name="CircleWithText",
        quality="low_quality",
        output_name="circle_with_text"
    )
    
    if text_video:
        print(f"✓ Circle with text animation generated: {text_video}")
    else:
        print("✗ Circle with text animation failed")


def test_mathematical_animations():
    """
    Test mathematical animations including function plots and transformations.
    
    This function demonstrates how to generate videos from
    mathematical animation scripts with different formats.
    """
    print("\nTesting mathematical animations...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Test function plot
    function_video = generator.generate_video(
        script_path="test/mathematical_animation.py",
        scene_name="FunctionPlot",
        quality="medium_quality",
        output_name="function_plot"
    )
    
    if function_video:
        print(f"✓ Function plot animation generated: {function_video}")
    else:
        print("✗ Function plot animation failed")
    
    # Test geometric transformations
    transform_video = generator.generate_video(
        script_path="test/mathematical_animation.py",
        scene_name="GeometricTransformations",
        quality="medium_quality",
        output_name="geometric_transformations"
    )
    
    if transform_video:
        print(f"✓ Geometric transformations animation generated: {transform_video}")
    else:
        print("✗ Geometric transformations animation failed")
    
    # Test complex number visualization
    complex_video = generator.generate_video(
        script_path="test/mathematical_animation.py",
        scene_name="ComplexNumberVisualization",
        quality="medium_quality",
        output_name="complex_numbers"
    )
    
    if complex_video:
        print(f"✓ Complex number visualization generated: {complex_video}")
    else:
        print("✗ Complex number visualization failed")


def test_text_animations():
    """
    Test text animations with various effects.
    
    This function demonstrates how to generate videos from
    text animation scripts with different effects.
    """
    print("\nTesting text animations...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Test typing animation
    typing_video = generator.generate_video(
        script_path="test/text_animation.py",
        scene_name="TypingAnimation",
        quality="low_quality",
        output_name="typing_animation"
    )
    
    if typing_video:
        print(f"✓ Typing animation generated: {typing_video}")
    else:
        print("✗ Typing animation failed")
    
    # Test text morphing
    morphing_video = generator.generate_video(
        script_path="test/text_animation.py",
        scene_name="TextMorphing",
        quality="low_quality",
        output_name="text_morphing"
    )
    
    if morphing_video:
        print(f"✓ Text morphing animation generated: {morphing_video}")
    else:
        print("✗ Text morphing animation failed")
    
    # Test color changing text
    color_video = generator.generate_video(
        script_path="test/text_animation.py",
        scene_name="ColorChangingText",
        quality="low_quality",
        output_name="color_changing_text"
    )
    
    if color_video:
        print(f"✓ Color changing text animation generated: {color_video}")
    else:
        print("✗ Color changing text animation failed")


def test_batch_generation():
    """
    Test batch generation of multiple videos.
    
    This function demonstrates how to generate multiple videos
    from a list of script configurations.
    """
    print("\nTesting batch generation...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Define batch configuration
    batch_config = [
        {
            "script_path": "test/basic_circle_animation.py",
            "scene_name": "BasicCircleAnimation",
            "quality": "low_quality",
            "output_name": "batch_circle"
        },
        {
            "script_path": "test/text_animation.py",
            "scene_name": "TypingAnimation",
            "quality": "low_quality",
            "output_name": "batch_typing"
        },
        {
            "script_path": "test/mathematical_animation.py",
            "scene_name": "FunctionPlot",
            "quality": "low_quality",
            "output_name": "batch_function"
        }
    ]
    
    # Generate batch videos
    generated_videos = generator.batch_generate(batch_config)
    
    print(f"Batch generation completed. Generated {len(generated_videos)} videos:")
    for video in generated_videos:
        print(f"  - {video}")


def test_string_based_generation():
    """
    Test video generation from script content strings.
    
    This function demonstrates how to generate videos directly
    from script content without creating temporary files.
    """
    print("\nTesting string-based generation...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Define a simple script as string
    simple_script = '''
from manim import *

class StringTestScene(Scene):
    def construct(self):
        # Create a simple animation
        square = Square(color=BLUE, fill_opacity=0.5)
        circle = Circle(color=RED, fill_opacity=0.5)
        
        # Position elements
        square.shift(LEFT)
        circle.shift(RIGHT)
        
        # Animation sequence
        self.play(Create(square), Create(circle), run_time=2)
        self.wait(1)
        self.play(square.animate.shift(RIGHT), circle.animate.shift(LEFT), run_time=2)
        self.wait(1)
        self.play(FadeOut(square), FadeOut(circle), run_time=1.5)
        self.wait(1)
'''
    
    # Generate video from string
    string_video = generator.generate_video_from_string(
        script_content=simple_script,
        scene_name="StringTestScene",
        quality="low_quality",
        output_name="string_test"
    )
    
    if string_video:
        print(f"✓ String-based video generated: {string_video}")
    else:
        print("✗ String-based video generation failed")


def test_different_formats():
    """
    Test video generation in different formats.
    
    This function demonstrates how to generate videos
    in different formats like MP4, GIF, and WebM.
    """
    print("\nTesting different formats...")
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="test_output")
    
    # Test MP4 format (default)
    mp4_video = generator.generate_video(
        script_path="test/basic_circle_animation.py",
        scene_name="BasicCircleAnimation",
        quality="low_quality",
        format="mp4",
        output_name="format_test_mp4"
    )
    
    if mp4_video:
        print(f"✓ MP4 video generated: {mp4_video}")
    else:
        print("✗ MP4 video generation failed")
    
    # Test GIF format
    gif_video = generator.generate_video(
        script_path="test/basic_circle_animation.py",
        scene_name="BasicCircleAnimation",
        quality="low_quality",
        format="gif",
        output_name="format_test_gif"
    )
    
    if gif_video:
        print(f"✓ GIF video generated: {gif_video}")
    else:
        print("✗ GIF video generation failed")


def main():
    """
    Main function to run all tests.
    
    This function orchestrates the execution of all test functions
    to demonstrate the complete functionality of the video generator.
    """
    print("=" * 60)
    print("Manim Video Generation Test Suite")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("test_output", exist_ok=True)
    
    try:
        # Run all tests
        test_basic_animations()
        test_mathematical_animations()
        test_text_animations()
        test_batch_generation()
        test_string_based_generation()
        test_different_formats()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("Check the 'test_output' directory for generated videos.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        print("Make sure Manim is properly installed and accessible.")


if __name__ == "__main__":
    main()



