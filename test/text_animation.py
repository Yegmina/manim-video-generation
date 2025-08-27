"""
Text Animation Example

This script demonstrates various text animations and effects
including typing, morphing, and color transitions.
"""

from manim import *


class TypingAnimation(Scene):
    """
    A scene demonstrating typing animation effects.
    
    This scene shows how to create typewriter-style text animations
    with different speeds and effects.
    """
    
    def construct(self):
        # Create text with typing animation
        title = Text(
            "Welcome to Manim",
            font_size=48,
            color=BLUE
        )
        
        subtitle = Text(
            "Mathematical Animation Engine",
            font_size=32,
            color=YELLOW
        ).next_to(title, DOWN, buff=0.5)
        
        # Animation sequence
        # Type the title
        self.play(Write(title), run_time=3)
        
        # Wait
        self.wait(1)
        
        # Type the subtitle
        self.play(Write(subtitle), run_time=2.5)
        
        # Wait
        self.wait(2)
        
        # Fade out
        self.play(
            FadeOut(title),
            FadeOut(subtitle),
            run_time=1.5
        )
        
        self.wait(1)


class TextMorphing(Scene):
    """
    A scene demonstrating text morphing and transformation.
    
    This scene shows how text can be transformed between
    different words with smooth morphing animations.
    """
    
    def construct(self):
        # Create initial text
        text1 = Text(
            "Hello",
            font_size=64,
            color=GREEN
        )
        
        # Create target text
        text2 = Text(
            "World",
            font_size=64,
            color=RED
        )
        
        # Create final text
        text3 = Text(
            "Manim",
            font_size=64,
            color=BLUE
        )
        
        # Animation sequence
        # Show first text
        self.play(Write(text1), run_time=2)
        
        # Wait
        self.wait(1)
        
        # Morph to second text
        self.play(TransformMatchingShapes(text1, text2), run_time=2)
        
        # Wait
        self.wait(1)
        
        # Morph to third text
        self.play(TransformMatchingShapes(text2, text3), run_time=2)
        
        # Wait
        self.wait(2)
        
        # Fade out
        self.play(FadeOut(text3), run_time=1.5)
        
        self.wait(1)


class ColorChangingText(Scene):
    """
    A scene demonstrating text color transitions.
    
    This scene shows how text colors can be animated
    with smooth transitions between different colors.
    """
    
    def construct(self):
        # Create text
        text = Text(
            "Colorful Animation",
            font_size=56,
            color=WHITE
        )
        
        # Show text
        self.play(Write(text), run_time=2)
        
        # Wait
        self.wait(1)
        
        # Change colors
        colors = [RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE]
        
        for color in colors:
            self.play(
                text.animate.set_color(color),
                run_time=1
            )
            self.wait(0.5)
        
        # Final wait
        self.wait(2)
        
        # Fade out
        self.play(FadeOut(text), run_time=1.5)
        
        self.wait(1)


class TextEffects(Scene):
    """
    A scene demonstrating various text effects.
    
    This scene shows different text effects including
    scaling, rotation, and position animations.
    """
    
    def construct(self):
        # Create text
        text = Text(
            "Effects",
            font_size=72,
            color=WHITE
        )
        
        # Show text
        self.play(Write(text), run_time=2)
        
        # Wait
        self.wait(1)
        
        # Scale up
        self.play(text.animate.scale(1.5), run_time=1.5)
        
        # Rotate
        self.play(Rotate(text, angle=PI/4), run_time=1.5)
        
        # Move around
        self.play(text.animate.shift(UP), run_time=1)
        self.play(text.animate.shift(RIGHT), run_time=1)
        self.play(text.animate.shift(DOWN), run_time=1)
        self.play(text.animate.shift(LEFT), run_time=1)
        
        # Return to original position and size
        self.play(
            text.animate.scale(1/1.5).rotate(-PI/4),
            run_time=2
        )
        
        # Wait
        self.wait(2)
        
        # Fade out
        self.play(FadeOut(text), run_time=1.5)
        
        self.wait(1)



