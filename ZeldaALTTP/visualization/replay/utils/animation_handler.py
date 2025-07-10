import os
import pygame
import json

# Constants
COLORKEY = (0, 0, 0)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')

def load_img(img_path, colorkey=COLORKEY):
    """Load an image and set its colorkey for transparency"""
    img = pygame.image.load(img_path)
    img.set_colorkey(colorkey)
    return img

class AnimationData:
    def __init__(self, path, colorkey=COLORKEY):
        """Initialize animation data from a directory of images and config"""
        # Load all PNG images from the directory
        self.img_list = []
        imgs = sorted([f for f in os.listdir(path) if f.startswith('img_') and f.endswith('.png')])
        
        for img in imgs:
            self.img_list.append([load_img(os.path.join(path, img), colorkey)])
        
        # Load or create config file
        json_path = os.path.join(path, f"_{os.path.basename(path)}.json")
        try:
            with open(json_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # Default configuration
            self.config = {
                'frames': [5 for _ in range(len(self.img_list))],
                'offset': [0, 0],
                'pause': False,
                'speed': 1,
                'loop': True
            }
            with open(json_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        
        # Create frame data with duration information
        self.frame_data = []
        total_frames = 0
        for n, num_frame in enumerate(self.config['frames']):
            total_frames += num_frame
            self.frame_data.append([total_frames, self.img_list[n][-1]])
        
        self.duration = sum(self.config['frames'])

class Animation:
    def __init__(self, animation_data):
        """Initialize an animation instance"""
        self.animation_data = animation_data
        self.frame = 0
        self.pause = animation_data.config['pause']
        self.loop = animation_data.config['loop']
        self.just_looped = False
        self.calc_img()
    
    def calc_img(self):
        """Calculate current image based on frame number"""
        for frame in self.animation_data.frame_data:
            duration = frame[0]
            if duration > self.frame:
                self.img = frame[1]
                break
        if self.animation_data.duration < self.frame:
            self.img = self.animation_data.frame_data[-1][1]
    
    def play(self, dt):
        """Update animation state"""
        self.just_looped = False
        if not self.pause:
            self.frame += dt * 60 * self.animation_data.config['speed']
        
        if self.loop:
            while self.frame > self.animation_data.duration:
                self.rewind()
                self.just_looped = True
        
        self.calc_img()
    
    def pause_play(self):
        """Toggle animation pause state"""
        self.pause = not self.pause
    
    def rewind(self):
        """Reset animation to start"""
        self.frame = 0

class AnimationManager:
    def __init__(self, base_path=None):
        """Initialize animation manager with all available animations"""
        if base_path is None:
            # Use the new @animation/link directory for Link animations
            base_path = os.path.join(ASSETS_DIR, 'animation', 'link')
        self.animation_data = {}
        animations = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
        for anime in animations:
            full_path = os.path.join(base_path, anime)
            self.animation_data[anime] = AnimationData(full_path, COLORKEY)
        # Load knight animations
        knight_base_path = os.path.join(ASSETS_DIR, 'animation', 'knights')
        if os.path.exists(knight_base_path):
            knight_types = [d for d in os.listdir(knight_base_path) if os.path.isdir(os.path.join(knight_base_path, d))]
            for knight_type in knight_types:
                idle_path = os.path.join(knight_base_path, knight_type, 'idle')
                if os.path.isdir(idle_path):
                    self.animation_data[f'{knight_type}_idle'] = AnimationData(idle_path, COLORKEY)
    
    def get_animation(self, animation_id):
        """Get a new animation instance by ID"""
        if animation_id in self.animation_data:
            return Animation(self.animation_data[animation_id])
        else:
            raise KeyError(f"Animation '{animation_id}' not found") 