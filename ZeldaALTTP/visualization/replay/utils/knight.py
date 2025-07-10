import pygame

class Knight:
    """
    Represents a stationary Knight that idly looks left and right (flips sprite).
    knight_type: 'dagger' or 'sword'
    """
    def __init__(self, x, y, animation_manager, sprite_scale=1.0, zoom_level=1.0, look_interval=2.0, knight_type='dagger'):
        """
        Args:
            x, y: Position in world coordinates.
            animation_manager: AnimationManager instance.
            sprite_scale: Base sprite scale.
            zoom_level: Initial zoom level.
            look_interval: Seconds between looking left/right.
            knight_type: 'dagger' or 'sword'
        """
        self.x = x
        self.y = y
        self.sprite_scale = sprite_scale
        self.zoom_level = zoom_level
        self.animation_manager = animation_manager
        self.knight_type = knight_type
        # Animation name is e.g. 'knight_dagger_idle' or 'knight_sword_idle'
        animation_name = f'knight_{knight_type}_idle'
        self.idle_animation = self.animation_manager.get_animation(animation_name)
        self.facing_left = False
        self.look_interval = look_interval
        self.look_timer = 0.0

    def update(self, dt):
        """
        Update the knight's idle animation and flip direction on timer.
        """
        self.idle_animation.play(dt)
        self.look_timer += dt
        if self.look_timer >= self.look_interval:
            self.facing_left = not self.facing_left
            self.look_timer = 0.0

    def draw(self, screen, camera):
        """
        Draw the knight at its current position, always facing the same direction in idle (no flipping).
        """
        img = self.idle_animation.img
        if img is not None:
            scale = self.sprite_scale * self.zoom_level
            img_scaled = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            # No flipping in idle
            screen_x, screen_y = camera.apply(int(self.x), int(self.y))
            rect = img_scaled.get_rect(center=(screen_x, screen_y))
            screen.blit(img_scaled, rect) 