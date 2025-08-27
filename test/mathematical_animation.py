"""
Mathematical Animation Example

This script demonstrates mathematical animations including
function plotting, coordinate systems, and mathematical transformations.
"""

from manim import *
import numpy as np


class FunctionPlot(Scene):
    """
    A scene demonstrating function plotting with coordinate axes.
    
    This scene shows how to create coordinate systems and plot
    mathematical functions with smooth animations.
    """
    
    def construct(self):
        # Create coordinate system
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 4, 1],
            x_length=6,
            y_length=4,
            axis_config={"color": WHITE}
        )
        
        # Add labels
        x_label = axes.get_x_axis_label("x")
        y_label = axes.get_y_axis_label("y")
        
        # Create function plot
        def func(x):
            return x**2 - 1
        
        graph = axes.plot(func, color=YELLOW, stroke_width=3)
        
        # Animation sequence
        # Show axes first
        self.play(Create(axes), run_time=2)
        self.play(Write(x_label), Write(y_label), run_time=1)
        
        # Show function plot
        self.play(Create(graph), run_time=3)
        
        # Wait
        self.wait(2)
        
        # Fade out
        self.play(
            FadeOut(axes),
            FadeOut(graph),
            FadeOut(x_label),
            FadeOut(y_label),
            run_time=1.5
        )
        
        self.wait(1)


class GeometricTransformations(Scene):
    """
    A scene demonstrating geometric transformations.
    
    This scene shows rotation, scaling, and translation
    of geometric shapes with smooth animations.
    """
    
    def construct(self):
        # Create a square
        square = Square(
            side_length=1,
            color=GREEN,
            fill_opacity=0.5
        )
        
        # Create a circle
        circle = Circle(
            radius=0.5,
            color=BLUE,
            fill_opacity=0.5
        ).next_to(square, RIGHT, buff=1)
        
        # Create a triangle
        triangle = Triangle(
            color=RED,
            fill_opacity=0.5
        ).next_to(square, LEFT, buff=1)
        
        # Show all shapes
        self.play(
            Create(square),
            Create(circle),
            Create(triangle),
            run_time=2
        )
        
        # Wait
        self.wait(1)
        
        # Rotate square
        self.play(Rotate(square, angle=PI/2), run_time=1.5)
        
        # Scale circle
        self.play(circle.animate.scale(1.5), run_time=1.5)
        
        # Move triangle
        self.play(triangle.animate.shift(UP), run_time=1.5)
        
        # Wait
        self.wait(2)
        
        # Fade out
        self.play(
            FadeOut(square),
            FadeOut(circle),
            FadeOut(triangle),
            run_time=1.5
        )
        
        self.wait(1)


class ComplexNumberVisualization(Scene):
    """
    A scene demonstrating complex number visualization.
    
    This scene shows complex numbers on the complex plane
    with their real and imaginary components.
    """
    
    def construct(self):
        # Create complex plane
        plane = ComplexPlane(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            background_line_style={
                "stroke_opacity": 0.6,
                "stroke_color": BLUE
            }
        )
        
        # Add labels
        real_label = Text("Re", font_size=24).next_to(plane.x_axis, DOWN)
        imag_label = Text("Im", font_size=24).next_to(plane.y_axis, LEFT)
        
        # Create complex numbers
        z1 = Dot(plane.c2p(2, 1), color=YELLOW, radius=0.1)
        z2 = Dot(plane.c2p(-1, 2), color=RED, radius=0.1)
        
        # Add labels for complex numbers
        z1_label = Text("2+i", font_size=20, color=YELLOW).next_to(z1, UR, buff=0.1)
        z2_label = Text("-1+2i", font_size=20, color=RED).next_to(z2, UL, buff=0.1)
        
        # Animation sequence
        # Show plane
        self.play(Create(plane), run_time=2)
        self.play(Write(real_label), Write(imag_label), run_time=1)
        
        # Show complex numbers
        self.play(
            Create(z1),
            Create(z2),
            run_time=1.5
        )
        
        self.play(
            Write(z1_label),
            Write(z2_label),
            run_time=1
        )
        
        # Wait
        self.wait(3)
        
        # Fade out
        self.play(
            FadeOut(plane),
            FadeOut(z1),
            FadeOut(z2),
            FadeOut(z1_label),
            FadeOut(z2_label),
            FadeOut(real_label),
            FadeOut(imag_label),
            run_time=1.5
        )
        
        self.wait(1)



