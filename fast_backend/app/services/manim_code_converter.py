import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ManimCodeConverter:
    """Converts deprecated Manim code to be compatible with v0.19.0+."""
    
    def __init__(self):
        # Define patterns and their replacements for Manim v0.19.0 compatibility
        self.replacements: List[Tuple[str, str]] = [
            # Axis label methods - these are the main culprits (will be handled by _add_axis_labels)
            (r'axes\.add_labels\(\)', r''),
            (r'axes\.add_coordinate_labels\(\)', r''),
            (r'axes\.coordinate_labels', r''),
            
            # Plot methods - these are commonly confused
            (r'axes\.plot_line\(', r'axes.plot('),
            (r'axes\.plot_curve\(', r'axes.plot('),
            
            # Coordinate fixes - 2D to 3D conversion for common patterns
            (r'start=\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)', r'start=(\1, \2, 0)'),
            (r'end=\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)', r'end=(\1, \2, 0)'),
            (r'\.move_to\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)', r'.move_to((\1, \2, 0))'),
            
            # Polygon coordinate fixes - convert 2D arrays to 3D
            (r'Polygon\(\s*\[(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\],\s*\[(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\],\s*\[(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\],\s*\[(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\]', 
             r'Polygon([\1, \2, 0], [\3, \4, 0], [\5, \6, 0], [\7, \8, 0]'),
            
            # Other deprecated methods
            (r'Code\.styles_list', r'Code.get_styles_list()'),
            (r'inner_radius\s*=', r'radius='),
            (r'outer_radius\s*=', r'radius='),
            (r'Scene\.next_section\(', r'Scene.next_section(section_type='),
            (r'VGroup\((.*?)\)', r'VGroup(*\1)'),
            (r'SurroundingRectangle\((.*?),(.*?),(.*?)\)', r'SurroundingRectangle(\1, color=\2, buff=\3)'),
            (r'OpenGLMobject', r'Mobject'),
            (r'OpenGLSurface', r'Surface'),
            (r'Mobject\.add_updater\((.*?)\)', r'Mobject.add_dt_updater(\1)'),
            (r'Scene\(\)\.render\(\)', r'Manager(Scene).render()'),
            
            # MathTex deprecation warnings (optional - keep but warn)
            (r'MathTex\((.*?)\)', r'Text(\1)'),
            (r'DashedLine\(', r'Line('),
        ]
    
    def convert_code(self, code: str) -> str:
        """
        Convert deprecated Manim code to v0.19.0+ compatible code.
        
        Args:
            code: The original Manim code
            
        Returns:
            Converted code that should work with Manim v0.19.0+
        """
        logger.info("Converting Manim code for v0.19.0+ compatibility")
        
        # Check if we need to handle axis labels
        needs_axis_fix = 'axes.add_labels()' in code or 'axes.add_coordinate_labels()' in code
        
        # Apply all replacements
        converted_code = code
        for pattern, replacement in self.replacements:
            converted_code = re.sub(pattern, replacement, converted_code, flags=re.MULTILINE)
        
        # Add axis labels if they were removed
        if needs_axis_fix:
            converted_code = self._add_axis_labels(converted_code)
        
        # Add imports if needed
        converted_code = self._ensure_imports(converted_code)

        # Fix Polygon coordinate arrays (2D to 3D conversion)
        converted_code = self._fix_polygon_coordinates(converted_code)

        # Inject helper for UpdateProgress if referenced by generated code
        if 'UpdateProgress(' in converted_code and 'class UpdateProgress' not in converted_code:
            helper = (
                "\nfrom manim import Animation, Text\n\n"
                "class UpdateProgress(Animation):\n"
                "    def __init__(self, text_mobject, formatter, run_time=1.0, **kwargs):\n"
                "        self.formatter = formatter\n"
                "        super().__init__(text_mobject, run_time=run_time, **kwargs)\n\n"
                "    def interpolate_mobject(self, alpha):\n"
                "        t = alpha * self.run_time\n"
                "        new_text = Text(self.formatter(t)).move_to(self.mobject.get_center())\n"
                "        self.mobject.become(new_text)\n\n"
            )
            converted_code = helper + converted_code
 
        logger.info("Manim code conversion completed")
        return converted_code
    
    def _add_axis_labels(self, code: str) -> str:
        """Add proper axis labels when deprecated methods are found."""
        # Split code into lines for easier processing
        lines = code.split('\n')
        new_lines = []
        
        # Process each line
        for line in lines:
            # Skip deprecated method calls
            if 'axes.add_coordinate_labels()' in line or 'axes.add_labels()' in line:
                continue
            
            new_lines.append(line)
            
            # After axes creation, add proper labels if they don't exist
            if 'axes = Axes(' in line and 'axes.get_x_axis_label(' not in code:
                new_lines.append('        x_label = axes.get_x_axis_label("Time (s)")')
                new_lines.append('        y_label = axes.get_y_axis_label("Position (m)")')
        
        # Reconstruct code
        code = '\n'.join(new_lines)
        
        # Add labels to scene if they exist but aren't added
        if 'x_label = axes.get_x_axis_label(' in code and 'self.add(x_label, y_label)' not in code:
            if 'self.play(Create(axes)' in code:
                code = code.replace('self.play(Create(axes))', 'self.play(Create(axes))\n        self.add(x_label, y_label)')
            elif 'self.add(axes' in code:
                code = re.sub(r'self\.add\(axes([^)]*)\)', r'self.add(axes\1, x_label, y_label)', code)
        
        return code
    
    def _fix_polygon_coordinates(self, code: str) -> str:
        """Fix Polygon coordinate arrays by converting 2D coordinates to 3D."""
        import re
        
        # Pattern to match Polygon constructor with 2D coordinate arrays
        # This matches: Polygon([x1, y1], [x2, y2], [x3, y3], ...)
        pattern = r'Polygon\(\s*((?:\[-?\d+(?:\.\d+)?,\s*-?\d+(?:\.\d+)?\](?:\s*,\s*)?)+)'
        
        def replace_coordinates(match):
            coordinates_str = match.group(1)
            # Split by commas and clean up
            coord_parts = coordinates_str.split('],')
            
            new_coords = []
            for part in coord_parts:
                # Clean up the part and extract x, y values
                part = part.strip().strip('[').strip(']')
                if ',' in part:
                    x, y = part.split(',')
                    x = x.strip()
                    y = y.strip()
                    new_coords.append(f'[{x}, {y}, 0]')
            
            return f'Polygon({", ".join(new_coords)}'
        
        # Apply the replacement
        fixed_code = re.sub(pattern, replace_coordinates, code)
        
        return fixed_code
    
    def _ensure_imports(self, code: str) -> str:
        """Ensure all necessary imports are present."""
        imports = []
        
        # Check what's being used and add imports if needed
        if 'Axes' in code and 'from manim import Axes' not in code:
            imports.append('Axes')
        if 'Text' in code and 'from manim import Text' not in code:
            imports.append('Text')
        if 'Circle' in code and 'from manim import Circle' not in code:
            imports.append('Circle')
        if 'Line' in code and 'from manim import Line' not in code:
            imports.append('Line')
        if 'Dot' in code and 'from manim import Dot' not in code:
            imports.append('Dot')
        
        # If we have specific imports to add, modify the import line
        if imports and 'from manim import *' in code:
            # Already using wildcard import, no changes needed
            pass
        elif imports and 'from manim import' in code:
            # Add to existing import
            current_imports = re.search(r'from manim import ([^\\n]+)', code)
            if current_imports:
                existing = current_imports.group(1).split(', ')
                all_imports = list(set(existing + imports))
                new_import_line = f'from manim import {", ".join(all_imports)}'
                code = re.sub(r'from manim import [^\\n]+', new_import_line, code)
        
        return code
    
    def validate_code(self, code: str) -> bool:
        """
        Validate that the code doesn't contain known deprecated methods.
        
        Args:
            code: The code to validate
            
        Returns:
            True if code appears to be compatible, False if deprecated methods found
        """
        deprecated_patterns = [
            r'axes\.add_labels\(\)',
            r'axes\.add_coordinate_labels\(\)',
            r'axes\.coordinate_labels',
            r'axes\.plot_line\(',
            r'axes\.plot_curve\(',
            r'start=\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)',  # 2D coordinates
            r'end=\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)',    # 2D coordinates
            r'Code\.styles_list',
            r'inner_radius\s*=',
            r'outer_radius\s*=',
            r'OpenGLMobject',
            r'OpenGLSurface',
        ]
        
        for pattern in deprecated_patterns:
            if re.search(pattern, code):
                logger.warning(f"Found deprecated pattern: {pattern}")
                return False
        
        return True


# Global converter instance
converter = ManimCodeConverter()


def convert_manim_code(code: str) -> str:
    """
    Convenience function to convert Manim code.
    
    Args:
        code: The original Manim code
        
    Returns:
        Converted code compatible with Manim v0.19.0+
    """
    return converter.convert_code(code)


def validate_manim_code(code: str) -> bool:
    """
    Convenience function to validate Manim code.
    
    Args:
        code: The code to validate
        
    Returns:
        True if code appears compatible, False if deprecated methods found
    """
    return converter.validate_code(code)
