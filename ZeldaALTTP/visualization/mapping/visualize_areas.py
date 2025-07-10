import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random
import colorsys
import json


def load_latest_area_map():
    """Load the most recent area map file"""
    latest_map = Path(__file__).resolve().parent / "area_maps" / "area_map.json"

    if not latest_map:
        raise FileNotFoundError("No area map files found")
        
    with open(latest_map) as f:
        return json.load(f)

class Area:
    def __init__(self, data):
        self.name = data["name"]
        self.x_range = data["x_range"]
        self.y_range = data["y_range"]
        self.is_interior = data.get("is_interior", False)

def create_area_visualization():
    # Load areas from the latest map file
    areas_data = load_latest_area_map()
    areas = {area_id: Area(area_data) for area_id, area_data in areas_data.items()}

    # Find the bounds of all areas
    min_x = min(area.x_range[0] for area in areas.values())
    max_x = max(area.x_range[1] for area in areas.values())
    min_y = min(area.y_range[0] for area in areas.values())
    max_y = max(area.y_range[1] for area in areas.values())

    # Add padding
    padding = 100
    width = max_x - min_x + 2 * padding
    height = max_y - min_y + 2 * padding

    # Create image
    img = Image.new('RGB', (width, height), 'black')
    draw = ImageDraw.Draw(img)

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Generate colors for different area types
    colors = generate_distinct_colors(len(areas))
    color_map = dict(zip(areas.keys(), colors))

    # Draw each area
    for area_id, area in areas.items():
        color = color_map[area_id]
        
        # Calculate coordinates relative to canvas
        x1 = area.x_range[0] - min_x + padding
        y1 = area.y_range[0] - min_y + padding
        x2 = area.x_range[1] - min_x + padding
        y2 = area.y_range[1] - min_y + padding

        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        
        # Draw area name
        text_x = (x1 + x2) // 2
        text_y = (y1 + y2) // 2
        
        # Draw text background for better visibility
        text_bbox = draw.textbbox((text_x, text_y), area.name, font=font, anchor="mm")
        draw.rectangle(text_bbox, fill='black')
        
        # Draw text
        draw.text((text_x, text_y), area.name, fill=color, font=font, anchor="mm")

    # Create a legend
    legend_img = Image.new('RGB', (400, len(areas) * 25 + 50), 'black')
    legend_draw = ImageDraw.Draw(legend_img)
    
    y = 25
    legend_draw.text((200, 10), "Area Legend", fill='white', font=font, anchor="mm")
    for area_id, area in areas.items():
        color = color_map[area_id]
        legend_draw.rectangle([10, y, 30, y + 20], fill=color)
        legend_draw.text((40, y + 10), f"{area_id} {'(interior)' if area.is_interior else ''}", 
                        fill='white', font=font, anchor="lm")
        y += 25

    # Combine main image and legend
    combined = Image.new('RGB', (width + legend_img.width, max(height, legend_img.height)), 'black')
    combined.paste(img, (0, 0))
    combined.paste(legend_img, (width, 0))

    # Save the image
    output_path = Path(__file__).parent / "area_visualization.png"
    combined.save(output_path)
    print(f"Visualization saved to: {output_path}")

def generate_distinct_colors(n):
    """Generate n visually distinct colors"""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7 + random.random() * 0.3
        value = 0.6 + random.random() * 0.2
        rgb = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hue, saturation, value))
        colors.append(rgb)
    return colors

if __name__ == "__main__":
    create_area_visualization() 