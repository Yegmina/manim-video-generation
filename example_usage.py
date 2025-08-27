"""
Example Usage of Manim Video Generation System

This script demonstrates how to use the ManimVideoGenerator class
to create videos from Manim scripts with different configurations.
"""

from manim_video_generator import ManimVideoGenerator, generate_manim_video


def example_basic_usage():
    """
    Demonstrate basic usage of the video generator.
    
    This function shows how to create a simple video using
    the convenience function.
    """
    print("Example 1: Basic Usage")
    print("-" * 40)
    
    # Generate a simple video using the convenience function
    video_path = generate_manim_video(
        script_path="test/basic_circle_animation.py",
        scene_name="BasicCircleAnimation",
        quality="low_quality",
        output_name="example_basic"
    )
    
    if video_path:
        print(f"✓ Video generated successfully: {video_path}")
    else:
        print("✗ Video generation failed")
    
    print()


def example_generator_class():
    """
    Demonstrate usage of the ManimVideoGenerator class.
    
    This function shows how to use the generator class for
    more advanced configurations.
    """
    print("Example 2: Using Generator Class")
    print("-" * 40)
    
    # Initialize the generator
    generator = ManimVideoGenerator(output_dir="example_output")
    
    # Generate video with custom settings
    video_path = generator.generate_video(
        script_path="test/text_animation.py",
        scene_name="TypingAnimation",
        quality="medium_quality",
        format="mp4",
        output_name="example_typing"
    )
    
    if video_path:
        print(f"✓ Video generated successfully: {video_path}")
    else:
        print("✗ Video generation failed")
    
    print()


def example_string_based():
    """
    Demonstrate string-based video generation.
    
    This function shows how to generate videos directly
    from script content strings.
    """
    print("Example 3: String-based Generation")
    print("-" * 40)
    
    # Define a simple script as string
    script_content = '''
from manim import *

class StringExampleScene(Scene):
    def construct(self):
        # Create a title
        title = Text("String-based Generation", font_size=48, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        
        # Create a square
        square = Square(color=RED, fill_opacity=0.5)
        self.play(Create(square))
        self.wait(1)
        
        # Transform square to circle
        circle = Circle(color=GREEN, fill_opacity=0.5)
        self.play(Transform(square, circle))
        self.wait(1)
        
        # Fade out everything
        self.play(FadeOut(title), FadeOut(circle))
        self.wait(1)
'''
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="example_output")
    
    # Generate video from string
    video_path = generator.generate_video_from_string(
        script_content=script_content,
        scene_name="StringExampleScene",
        quality="low_quality",
        output_name="example_string"
    )
    
    if video_path:
        print(f"✓ Video generated successfully: {video_path}")
    else:
        print("✗ Video generation failed")
    
    print()


def example_batch_generation():
    """
    Demonstrate batch generation of multiple videos.
    
    This function shows how to generate multiple videos
    from a list of script configurations.
    """
    print("Example 4: Batch Generation")
    print("-" * 40)
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="example_output")
    
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
            "scene_name": "ColorChangingText",
            "quality": "low_quality",
            "output_name": "batch_color_text"
        },
        {
            "script_path": "test/mathematical_animation.py",
            "scene_name": "GeometricTransformations",
            "quality": "low_quality",
            "output_name": "batch_transformations"
        }
    ]
    
    # Generate batch videos
    generated_videos = generator.batch_generate(batch_config)
    
    print(f"Batch generation completed. Generated {len(generated_videos)} videos:")
    for i, video in enumerate(generated_videos, 1):
        print(f"  {i}. {video}")
    
    print()


def example_different_formats():
    """
    Demonstrate generation in different formats.
    
    This function shows how to generate videos
    in different formats (MP4, GIF).
    """
    print("Example 5: Different Formats")
    print("-" * 40)
    
    # Initialize generator
    generator = ManimVideoGenerator(output_dir="example_output")
    
    # Test MP4 format
    mp4_video = generator.generate_video(
        script_path="test/basic_circle_animation.py",
        scene_name="BasicCircleAnimation",
        quality="low_quality",
        format="mp4",
        output_name="format_example_mp4"
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
        output_name="format_example_gif"
    )
    
    if gif_video:
        print(f"✓ GIF video generated: {gif_video}")
    else:
        print("✗ GIF video generation failed")
    
    print()


def main():
    """
    Main function to run all examples.
    
    This function orchestrates the execution of all example functions
    to demonstrate the complete functionality of the video generator.
    """
    print("=" * 60)
    print("Manim Video Generation - Example Usage")
    print("=" * 60)
    print()
    
    try:
        # Run all examples
        example_basic_usage()
        example_generator_class()
        example_string_based()
        example_batch_generation()
        example_different_formats()
        
        print("=" * 60)
        print("All examples completed!")
        print("Check the 'example_output' directory for generated videos.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during examples: {e}")
        print("Make sure Manim is properly installed and accessible.")
        print("Run 'manim --version' to verify installation.")


if __name__ == "__main__":
    main()



