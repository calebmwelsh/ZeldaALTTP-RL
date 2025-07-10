import os
import sys


import pygame
from animation_handler import AnimationManager

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
SCALE = 3  # Scale factor for sprites

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Link Animation Example")
clock = pygame.time.Clock()

def scale_image(image, scale_factor):
    """Scale an image up by the given factor while maintaining pixel sharpness"""
    return pygame.transform.scale(image, 
                                (image.get_width() * scale_factor, 
                                 image.get_height() * scale_factor))

def main():
    # Initialize animation manager and load animations
    manager = AnimationManager()
    
    # Get animations for each direction
    animations = {
        'down': manager.get_animation('run_down'),
        'up': manager.get_animation('run_up'),
        'right': manager.get_animation('run_horizontal')
    }
    # Left animation is just flipped right animation
    animations['left'] = manager.get_animation('run_horizontal')
    
    # Initial position and direction
    pos_x = SCREEN_WIDTH // 2
    pos_y = SCREEN_HEIGHT // 2
    current_direction = 'down'
    facing_left = False
    
    # Movement speed (pixels per second)
    SPEED = 50 * SCALE  # Scale speed to match sprite scale
    
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Example of pausing animation
                    animations[current_direction].pause_play()
                elif event.key == pygame.K_ESCAPE:
                    # Exit on ESC key
                    running = False
        
        # Get time since last frame
        dt = clock.get_time() / 1000.0  # Convert to seconds
        
        # Handle movement
        keys = pygame.key.get_pressed()
        moving = False
        new_direction = current_direction
        
        if keys[pygame.K_LEFT]:
            pos_x -= SPEED * dt
            new_direction = 'left'
            facing_left = True
            moving = True
        elif keys[pygame.K_RIGHT]:
            pos_x += SPEED * dt
            new_direction = 'right'
            facing_left = False
            moving = True
        
        if keys[pygame.K_UP]:
            pos_y -= SPEED * dt
            new_direction = 'up'
            moving = True
        elif keys[pygame.K_DOWN]:
            pos_y += SPEED * dt
            new_direction = 'down'
            moving = True
        
        # Keep player on screen
        pos_x = max(0, min(pos_x, SCREEN_WIDTH))
        pos_y = max(0, min(pos_y, SCREEN_HEIGHT))
        
        # Update animation
        if moving:
            if new_direction != current_direction:
                animations[new_direction].rewind()
            current_direction = new_direction
            animations[current_direction].play(dt)
        else:
            # Reset animation when not moving
            animations[current_direction].rewind()
        
        # Clear screen
        screen.fill(BLACK)
        
        # Get current frame and scale it
        current_img = animations[current_direction].img
        current_img = scale_image(current_img, SCALE)
        
        # Flip image if facing left
        if facing_left:
            current_img = pygame.transform.flip(current_img, True, False)
        
        # Draw current frame centered on position
        img_rect = current_img.get_rect()
        img_rect.center = (int(pos_x), int(pos_y))
        screen.blit(current_img, img_rect)
        
        # Update display
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main() 