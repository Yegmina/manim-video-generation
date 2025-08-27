"""
Manim Video Generation Module

This module provides a comprehensive interface for generating videos using Manim,
a mathematical animation engine for creating explanatory math videos.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManimVideoGenerator:
    """
    A class for generating videos using Manim with various configuration options.
    
    This class provides methods to execute Manim scripts and generate video files
    with different quality settings, formats, and rendering options.
    """
    
    def __init__(self, output_dir: str = "output", manim_path: Optional[str] = None):
        """
        Initialize the Manim video generator.
        
        Parameters:
            output_dir (str): Directory where generated videos will be saved
            manim_path (str, optional): Path to Manim executable if not in PATH
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Use Python module approach for Windows compatibility
        if manim_path:
            self.manim_path = manim_path
        else:
            # Try to use Python module approach first
            try:
                import manim
                self.manim_path = "py"
                self.manim_module = True
            except ImportError:
                self.manim_path = "manim"
                self.manim_module = False
        
        # Verify Manim installation
        self._verify_manim_installation()
    
    def _verify_manim_installation(self) -> bool:
        """
        Verify that Manim is properly installed and accessible.
        
        Returns:
            bool: True if Manim is available, False otherwise
        """
        try:
            if hasattr(self, 'manim_module') and self.manim_module:
                # Use Python module approach
                cmd = [self.manim_path, "-m", "manim", "--version"]
            else:
                # Use direct command approach
                cmd = [self.manim_path, "--version"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Manim version: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Manim verification failed: {result.stderr}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Manim not found or not accessible: {e}")
            return False
    
    def generate_video(
        self,
        script_path: str,
        scene_name: str,
        quality: str = "medium_quality",
        format: str = "mp4",
        output_name: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate a video from a Manim script.
        
        Parameters:
            script_path (str): Path to the Manim script file
            scene_name (str): Name of the scene class to render
            quality (str): Video quality (low_quality, medium_quality, high_quality, production_quality)
            format (str): Output format (mp4, gif, webm)
            output_name (str, optional): Custom output filename
            extra_args (List[str], optional): Additional command line arguments
            
        Returns:
            str: Path to the generated video file, or None if generation failed
        """
        if not os.path.exists(script_path):
            logger.error(f"Script file not found: {script_path}")
            return None
        
        # Map quality settings to new Manim format
        quality_map = {
            "low_quality": "l",
            "medium_quality": "m", 
            "high_quality": "h",
            "production_quality": "p"
        }
        quality_flag = quality_map.get(quality, "m")
        
        # Prepare command arguments - always use Python module approach for Windows
        cmd = [
            self.manim_path,
            "-m",
            "manim",
            "render",
            script_path,
            scene_name,
            f"-q{quality_flag}",
            f"-o{output_name}" if output_name else "",
            "--format", format
        ]
        
        # Add extra arguments if provided
        if extra_args:
            cmd.extend(extra_args)
        
        # Filter out empty strings
        cmd = [arg for arg in cmd if arg]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        try:
            # Use absolute path for script
            abs_script_path = os.path.abspath(script_path)
            
            # Update command with absolute path
            cmd = [
                self.manim_path,
                "-m",
                "manim",
                "render",
                abs_script_path,
                scene_name,
                f"-q{quality_flag}",
                f"-o{output_name}" if output_name else "",
                "--format", format
            ]
            
            # Add extra arguments if provided
            if extra_args:
                cmd.extend(extra_args)
            
            # Filter out empty strings
            cmd = [arg for arg in cmd if arg]
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            
            # Execute Manim command from current directory
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                # Find the generated video file
                video_file = self._find_generated_video(script_path, scene_name, format)
                if video_file:
                    logger.info(f"Video generated successfully: {video_file}")
                    return str(video_file)
                else:
                    logger.warning("Video generation completed but file not found")
                    return None
            else:
                logger.error(f"Video generation failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Video generation timed out")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during video generation: {e}")
            return None
    
    def _find_generated_video(self, script_path: str, scene_name: str, format: str) -> Optional[Path]:
        """
        Find the generated video file in the media directory.
        
        Parameters:
            script_path (str): Path to the original script
            scene_name (str): Name of the scene
            format (str): Video format
            
        Returns:
            Path: Path to the generated video file
        """
        script_name = Path(script_path).stem
        media_dir = Path("media")
        
        if not media_dir.exists():
            return None
        
        # Look for video file in media directory
        # New Manim version uses different directory structure
        videos_dir = media_dir / "videos"
        if not videos_dir.exists():
            return None
        
        # Look for script-specific directory
        script_dir = videos_dir / script_name
        if script_dir.exists():
            # Look in quality subdirectories (e.g., 480p15, 720p30)
            for quality_dir in script_dir.iterdir():
                if quality_dir.is_dir():
                    # Look for video file with output name or scene name
                    for video_file in quality_dir.glob(f"*.{format}"):
                        return video_file
        
        # If no script-specific directory, look in all video directories
        for video_dir in videos_dir.iterdir():
            if video_dir.is_dir():
                for quality_dir in video_dir.iterdir():
                    if quality_dir.is_dir():
                        for video_file in quality_dir.glob(f"*.{format}"):
                            # Check if this file matches our scene or output name
                            if scene_name.lower() in video_file.name.lower():
                                return video_file
        
        return None
    
    def generate_video_from_string(
        self,
        script_content: str,
        scene_name: str,
        quality: str = "medium_quality",
        format: str = "mp4",
        output_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a video from a script content string.
        
        Parameters:
            script_content (str): Manim script content as string
            scene_name (str): Name of the scene class to render
            quality (str): Video quality
            format (str): Output format
            output_name (str, optional): Custom output filename
            
        Returns:
            str: Path to the generated video file, or None if generation failed
        """
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(script_content)
            temp_script_path = temp_file.name
        
        try:
            return self.generate_video(
                temp_script_path,
                scene_name,
                quality,
                format,
                output_name
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_script_path):
                os.unlink(temp_script_path)
    
    def batch_generate(
        self,
        scripts_config: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate multiple videos from a list of script configurations.
        
        Parameters:
            scripts_config (List[Dict]): List of script configurations with keys:
                - script_path: Path to script file
                - scene_name: Scene class name
                - quality: Video quality (optional)
                - format: Output format (optional)
                - output_name: Custom output name (optional)
                
        Returns:
            List[str]: List of paths to generated video files
        """
        generated_videos = []
        
        for config in scripts_config:
            logger.info(f"Processing script: {config.get('script_path', 'Unknown')}")
            
            video_path = self.generate_video(
                script_path=config['script_path'],
                scene_name=config['scene_name'],
                quality=config.get('quality', 'medium_quality'),
                format=config.get('format', 'mp4'),
                output_name=config.get('output_name')
            )
            
            if video_path:
                generated_videos.append(video_path)
        
        return generated_videos


def generate_manim_video(
    script_path: str,
    scene_name: str,
    output_dir: str = "output",
    quality: str = "medium_quality",
    format: str = "mp4",
    output_name: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function to generate a single Manim video.
    
    Parameters:
        script_path (str): Path to the Manim script
        scene_name (str): Name of the scene class
        output_dir (str): Output directory for videos
        quality (str): Video quality setting
        format (str): Output format
        output_name (str, optional): Custom output filename
        
    Returns:
        str: Path to the generated video file, or None if generation failed
    """
    generator = ManimVideoGenerator(output_dir=output_dir)
    return generator.generate_video(
        script_path=script_path,
        scene_name=scene_name,
        quality=quality,
        format=format,
        output_name=output_name
    )


if __name__ == "__main__":
    # Example usage
    generator = ManimVideoGenerator()
    
    # Test with a simple script
    test_script = '''
from manim import *

class TestScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(2)
'''
    
    video_path = generator.generate_video_from_string(
        test_script,
        "TestScene",
        quality="low_quality"
    )
    
    if video_path:
        print(f"Test video generated: {video_path}")
    else:
        print("Test video generation failed")
