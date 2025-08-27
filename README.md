# Manim Video Generation System

A comprehensive Python system for generating mathematical animations and videos using Manim, a powerful mathematical animation engine.

## Overview

This system provides a flexible and easy-to-use interface for creating mathematical animations, educational videos, and visual demonstrations using Manim. The system includes a main video generation module and a collection of example scripts demonstrating various animation techniques.

## Features

- **Flexible Video Generation**: Generate videos from Manim scripts with customizable quality and format settings
- **Batch Processing**: Generate multiple videos from a list of script configurations
- **String-based Generation**: Create videos directly from script content strings
- **Multiple Formats**: Support for MP4, GIF, and WebM output formats
- **Quality Control**: Different quality presets (low, medium, high, production)
- **Comprehensive Examples**: Collection of example scripts demonstrating various animation techniques

## Installation

### Prerequisites

1. **Python 3.8 or higher**
2. **FFmpeg** (required for video processing)

### Install FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
# Using Homebrew
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Verify Installation

```bash
manim --version
```

## Quick Start

### Basic Usage

```python
from manim_video_generator import generate_manim_video

# Generate a simple video
video_path = generate_manim_video(
    script_path="test/basic_circle_animation.py",
    scene_name="BasicCircleAnimation",
    quality="low_quality"
)

if video_path:
    print(f"Video generated: {video_path}")
```

### Using the Generator Class

```python
from manim_video_generator import ManimVideoGenerator

# Initialize generator
generator = ManimVideoGenerator(output_dir="my_videos")

# Generate video
video_path = generator.generate_video(
    script_path="my_script.py",
    scene_name="MyScene",
    quality="medium_quality",
    format="mp4"
)
```

### String-based Generation

```python
script_content = '''
from manim import *

class MyScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(2)
'''

video_path = generator.generate_video_from_string(
    script_content=script_content,
    scene_name="MyScene",
    quality="low_quality"
)
```

## Example Scripts

The `test/` directory contains various example scripts demonstrating different animation techniques:

### Basic Animations (`test/basic_circle_animation.py`)
- `BasicCircleAnimation`: Simple circle creation and transformation
- `CircleWithText`: Circle animation with accompanying text

### Mathematical Animations (`test/mathematical_animation.py`)
- `FunctionPlot`: Function plotting with coordinate axes
- `GeometricTransformations`: Rotation, scaling, and translation of shapes
- `ComplexNumberVisualization`: Complex numbers on the complex plane

### Text Animations (`test/text_animation.py`)
- `TypingAnimation`: Typewriter-style text animations
- `TextMorphing`: Text transformation between different words
- `ColorChangingText`: Text color transitions
- `TextEffects`: Various text effects (scaling, rotation, movement)

## Running Examples

### Run All Tests

```bash
py test/test_runner.py
```

### Run Individual Examples

```bash
# Basic circle animation
manim test/basic_circle_animation.py BasicCircleAnimation -ql

# Function plot
manim test/mathematical_animation.py FunctionPlot -qm

# Text animation
manim test/text_animation.py TypingAnimation -ql
```

### Using the Video Generator

```bash
# Run the test suite
py test/test_runner.py
```

## API Reference

### ManimVideoGenerator Class

#### Constructor
```python
ManimVideoGenerator(output_dir="output", manim_path=None)
```

**Parameters:**
- `output_dir` (str): Directory for generated videos
- `manim_path` (str, optional): Path to Manim executable

#### Methods

##### generate_video()
```python
generate_video(script_path, scene_name, quality="medium_quality", 
              format="mp4", output_name=None, extra_args=None)
```

**Parameters:**
- `script_path` (str): Path to Manim script file
- `scene_name` (str): Name of the scene class to render
- `quality` (str): Video quality (`low_quality`, `medium_quality`, `high_quality`, `production_quality`)
- `format` (str): Output format (`mp4`, `gif`, `webm`)
- `output_name` (str, optional): Custom output filename
- `extra_args` (List[str], optional): Additional command line arguments

**Returns:**
- `str`: Path to generated video file, or `None` if generation failed

##### generate_video_from_string()
```python
generate_video_from_string(script_content, scene_name, quality="medium_quality", 
                          format="mp4", output_name=None)
```

**Parameters:**
- `script_content` (str): Manim script content as string
- `scene_name` (str): Name of the scene class to render
- `quality` (str): Video quality setting
- `format` (str): Output format
- `output_name` (str, optional): Custom output filename

**Returns:**
- `str`: Path to generated video file, or `None` if generation failed

##### batch_generate()
```python
batch_generate(scripts_config)
```

**Parameters:**
- `scripts_config` (List[Dict]): List of script configurations

**Returns:**
- `List[str]`: List of paths to generated video files

### Convenience Function

#### generate_manim_video()
```python
generate_manim_video(script_path, scene_name, output_dir="output", 
                    quality="medium_quality", format="mp4", output_name=None)
```

**Parameters:**
- `script_path` (str): Path to the Manim script
- `scene_name` (str): Name of the scene class
- `output_dir` (str): Output directory for videos
- `quality` (str): Video quality setting
- `format` (str): Output format
- `output_name` (str, optional): Custom output filename

**Returns:**
- `str`: Path to the generated video file, or `None` if generation failed

## Quality Settings

- **`low_quality`**: Fast rendering, lower resolution (480p)
- **`medium_quality`**: Balanced quality and speed (720p)
- **`high_quality`**: Higher quality, slower rendering (1080p)
- **`production_quality`**: Highest quality, slowest rendering (4K)

## Output Formats

- **`mp4`**: Standard video format, good compression
- **`gif`**: Animated GIF, smaller file size
- **`webm`**: Web-optimized format, good compression

## Creating Custom Animations

### Basic Scene Structure

```python
from manim import *

class MyCustomScene(Scene):
    def construct(self):
        # Create objects
        circle = Circle(color=BLUE)
        square = Square(color=RED)
        
        # Animation sequence
        self.play(Create(circle))
        self.wait(1)
        self.play(Transform(circle, square))
        self.wait(1)
        self.play(FadeOut(square))
```

### Common Animation Techniques

#### Creating Objects
```python
# Create with animation
self.play(Create(circle))

# Show instantly
self.add(circle)
```

#### Transforming Objects
```python
# Scale
self.play(circle.animate.scale(2))

# Rotate
self.play(Rotate(circle, angle=PI/2))

# Move
self.play(circle.animate.shift(UP))
```

#### Text Animations
```python
# Type text
self.play(Write(text))

# Fade text
self.play(FadeIn(text))
```

#### Mathematical Objects
```python
# Coordinate system
axes = Axes(x_range=[-3, 3], y_range=[-2, 2])

# Function plot
graph = axes.plot(lambda x: x**2, color=YELLOW)

# Mathematical expressions
formula = MathTex(r"E = mc^2")
```

## Troubleshooting

### Common Issues

1. **Manim not found**: Ensure Manim is properly installed and in PATH
2. **FFmpeg not found**: Install FFmpeg and ensure it's in PATH
3. **Import errors**: Check that all dependencies are installed
4. **Video not generated**: Check script syntax and scene name

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Manual Manim Execution

Test scripts manually:
```bash
manim my_script.py MyScene -ql --preview
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Include tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Manim Community](https://github.com/ManimCommunity/manim) - The mathematical animation engine
- [3Blue1Brown](https://www.3blue1brown.com/) - Inspiration for mathematical animations



