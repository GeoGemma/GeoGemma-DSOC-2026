import logging

logger = logging.getLogger(__name__)

def create_visualization_response(tile_url, metadata):
    """
    Creates a standardized visualization response
    
    Args:
        tile_url: The URL for the map tiles
        metadata: Dictionary containing visualization metadata
        
    Returns:
        Dictionary with visualization parameters
    """
    response = {
        'tileUrl': tile_url,
        'bands': metadata.get('bands'),
        'palette': metadata.get('palette'),
        'min': metadata.get('min', 0),
        'max': metadata.get('max', 3000),
        'bbox': metadata.get('bbox'),
        'class_descriptions': metadata.get('class_descriptions'),
        'lookat': metadata.get('lookat'),
        'is_feature_collection': metadata.get('is_feature_collection', False),
        'feature_properties': metadata.get('feature_properties', [])
    }
    
    return response

def generate_legend_html(palette, min_val, max_val, class_descriptions=None):
    """
    Generates HTML for a color legend
    
    Args:
        palette: List of color codes
        min_val: Minimum value for the legend
        max_val: Maximum value for the legend
        class_descriptions: Optional class descriptions for discrete legends
        
    Returns:
        HTML string for the legend
    """
    if not palette or not isinstance(palette, list) or len(palette) == 0:
        return "<p>No palette information available.</p>"
    
    html = '<div class="palette-container">' + \
           '<div class="palette-title">Color Palette</div>'
    
    # If we have class descriptions, display them as a legend
    if class_descriptions and isinstance(class_descriptions, list):
        html += '<table style="width:100%; margin-bottom:10px; font-size:12px;">'
        for cls in class_descriptions:
            if 'color' in cls and 'description' in cls:
                color = cls['color']
                if not color.startswith('#'):
                    color = '#' + color
                html += f'<tr>' + \
                       f'<td style="width:20px; background-color:{color};">&nbsp;</td>' + \
                       f'<td style="padding-left:5px;">{cls["description"]} (Value: {cls.get("value", "N/A")})</td>' + \
                       f'</tr>'
        html += '</table>'
    else:
        # Otherwise display the simple color ramp
        html += '<div class="palette-display">'
        
        # Create color blocks for each color in the palette
        for color in palette:
            html += f'<div class="palette-color" style="background-color:{color}"></div>'
        
        html += '</div>' + \
                '<div class="palette-labels">' + \
                f'<span>{min_val}</span>' + \
                f'<span>{max_val}</span>' + \
                '</div>'
    
    html += '</div>'
    return html
