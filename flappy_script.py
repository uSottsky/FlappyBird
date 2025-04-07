import pygame
import os
import sys
import math
import random

class GameAssetManager:
    """Handles all asset loading with proper error handling and fallbacks."""
    
    def __init__(self):
        """Initialize the asset manager."""
        pass
        
    def get_asset_path(self, filename):
        """Return the correct path for an asset file in the root directory."""
        # Try direct path in the root folder
        if os.path.exists(filename):
            return filename
            
        # Try from script directory as fallback
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, filename)
        if os.path.exists(script_path):
            return script_path
            
        # Return the direct path anyway (will fail, but with a clearer error)
        return filename
        
    def load_image(self, filename, fallback=None):
        """Load an image with fallback options."""
        try:
            image = pygame.image.load(self.get_asset_path(filename))
            return image
        except (pygame.error, FileNotFoundError):
            print(f"Warning: Could not load {filename}")
            if fallback:
                return self.load_image(fallback)
            else:
                # Create a dummy surface as last resort
                dummy = pygame.Surface((100, 100))
                dummy.fill((255, 0, 0))
                return dummy
                
    def load_sound(self, filename, volume=1.0, fallback=None):
        """Load a sound with fallback options."""
        try:
            sound = pygame.mixer.Sound(self.get_asset_path(filename))
            sound.set_volume(volume)
            return sound
        except (pygame.error, FileNotFoundError):
            if fallback:
                return self.load_sound(fallback, volume)
            else:
                print(f"Warning: Could not load {filename}")
                dummy_sound = pygame.mixer.Sound(buffer=bytes(bytearray(16)))
                dummy_sound.set_volume(0)
                return dummy_sound


class GameConfig:
    """Manages all game configuration and theme-specific settings."""
    
    def __init__(self, is_night_theme=True):
        """Initialize game configuration with theme settings."""
        # Theme settings
        self.is_night_theme = is_night_theme
        
        # Physics constants (same for both themes)
        self.gravitational_force = 5
        self.jump_velocity = -40
        self.scroll_speed = 13
        
        # Bird sizing
        self.base_bird_size_percentage = 0.1
        
        # Animation settings
        self.max_upward_angle = 45
        self.max_downward_angle = -90
        self.rotation_speed = 3
        self.downward_rotation_speed = 10
        
    def update_theme_settings(self):
        """Update game settings based on current theme."""
        # No physics settings to update since they're the same for both themes
        pass
        
    def toggle_theme(self):
        """Toggle between day and night themes."""
        self.is_night_theme = not self.is_night_theme
        # No need to call update_theme_settings since physics don't change


class BackgroundManager:
    """Manages background, land and other environment elements."""
    
    def __init__(self, assets, config, screen_width, screen_height):
        """Initialize background manager."""
        self.assets = assets
        self.config = config
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.land_height = int(screen_height * 0.17)
        
        # Load assets
        self.load_assets()
        
        # Scrolling variables
        self.land_scroll = 0
        
    def load_assets(self):
        """Load background assets based on current theme."""
        # Background
        bg_filename = 'background-night.png' if self.config.is_night_theme else 'dayBackground.png'
        self.background_img = self.assets.load_image(bg_filename)
        self.background_img = pygame.transform.scale(self.background_img, (self.screen_width, self.screen_height))
        
        # Tap to start
        self.tap_to_start_img = self.assets.load_image('tapToStart.png')
        tap_width = self.screen_width // 2
        tap_height = int(tap_width * self.tap_to_start_img.get_height() / self.tap_to_start_img.get_width())
        self.tap_to_start_img = pygame.transform.scale(self.tap_to_start_img, (tap_width, tap_height))
        
        # Land
        self.land_img = self.assets.load_image('land.png')
        self.land_img = pygame.transform.scale(self.land_img, (self.screen_width, self.land_height))
        
    def update(self, dt, game_state):
        """Update background elements."""
        # Only scroll in certain game states
        if game_state != 2:  # Not in GAME_OVER state
            self.land_scroll -= self.config.scroll_speed
            if self.land_scroll <= -self.screen_width:
                self.land_scroll = 0
                
    def draw(self, surface):
        """Draw background elements (sky only)."""
        # Background
        surface.blit(self.background_img, (0, 0))
    
    def draw_land(self, surface):
        """Draw land element (separate from background)."""
        # Land (draw two copies for seamless scrolling)
        land_y = self.screen_height - self.land_height
        surface.blit(self.land_img, (self.land_scroll, land_y))
        surface.blit(self.land_img, (self.land_scroll + self.screen_width, land_y))
        
    def draw_tap_to_start(self, surface):
        """Draw tap to start message."""
        tap_x = (self.screen_width - self.tap_to_start_img.get_width()) // 2
        tap_y = (self.screen_height - self.tap_to_start_img.get_height()) // 2
        surface.blit(self.tap_to_start_img, (tap_x, tap_y))
        
    def check_land_collision(self, bird):
        """Check if the bird collides with the land."""
        land_y = self.screen_height - self.land_height
        
        # Check if bird's bottom edge is below the top of the land
        if bird.y + bird.current_img.get_height() > land_y:
            return True, land_y
        return False, land_y


class Bird:
    """Manages bird animations, physics and rendering."""
    
    def __init__(self, assets, config, screen_width, screen_height):
        """Initialize bird object."""
        self.assets = assets
        self.config = config
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Physics variables
        self.velocity = 0
        self.angle = 0
        
        # Animation state
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 100  # milliseconds per frame
        self.last_action = 0  # 0 = neutral, 1 = jump, -1 = falling
        
        # Load bird images and set position
        self.load_images()
        self.reset_position()
        
    def load_images(self):
        """Load bird images based on theme."""
        # Choose bird color based on theme
        bird_prefix = "redbird-" if self.config.is_night_theme else "yellowbird-"
        
        # Load bird images
        self.downflap_img = self.assets.load_image(f'{bird_prefix}downflap.png', 'bluebird-downflap.png')
        self.midflap_img = self.assets.load_image(f'{bird_prefix}midflap.png', 'bluebird-midflap.png')
        self.upflap_img = self.assets.load_image(f'{bird_prefix}upflap.png', 'bluebird-upflap.png')
        
        # Scale the bird images
        target_width = int(self.screen_width * self.config.base_bird_size_percentage)
        scale_factor = target_width / self.downflap_img.get_width()
        
        self.downflap_img = pygame.transform.scale(self.downflap_img, 
                                                  (target_width, 
                                                   int(self.downflap_img.get_height() * scale_factor)))
        self.midflap_img = pygame.transform.scale(self.midflap_img, 
                                                 (target_width, 
                                                  int(self.midflap_img.get_height() * scale_factor)))
        self.upflap_img = pygame.transform.scale(self.upflap_img, 
                                                (target_width, 
                                                 int(self.upflap_img.get_height() * scale_factor)))
                                                 
        # Set up animation frames
        self.animation_frames = [self.downflap_img, self.midflap_img, self.upflap_img, self.midflap_img]
        self.current_img = self.midflap_img
        
    def reset_position(self):
        """Reset bird to starting position."""
        self.x = self.screen_width // 2 - self.midflap_img.get_width() // 2
        self.y = (self.screen_height // 2 - self.midflap_img.get_height() // 2) - int(self.screen_height * 0.10)
        self.velocity = 0
        self.angle = 0
        self.current_img = self.midflap_img
        
    def jump(self):
        """Make the bird jump."""
        self.velocity = self.config.jump_velocity
        self.angle = self.config.max_upward_angle
        self.current_img = self.downflap_img
        self.last_action = 1
        
    def update_animation(self, current_time):
        """Update bird animation frame."""
        if current_time - self.animation_timer > self.animation_speed:
            self.animation_timer = current_time
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            
    def update(self, dt, game_state):
        """Update bird physics and animation."""
        if game_state == 0:  # START state
            # Just animate without physics
            return
            
        # Remember previous position to determine direction
        prev_y = self.y
        
        # Apply gravity with original physics
        gravity_mult = 1.5 if game_state == 2 else 1  # Higher gravity in GAME_OVER
        self.velocity += self.config.gravitational_force * gravity_mult
        self.y += int(self.velocity)
        
        # Update bird image based on movement
        if self.last_action == 1:  # Just jumped
            self.current_img = self.downflap_img
            self.last_action = 0
        elif self.y < prev_y:  # Moving upward
            self.current_img = self.midflap_img
        else:  # Falling
            self.current_img = self.upflap_img
            
        # Update bird angle
        if game_state == 2:  # GAME_OVER
            # Bird always rotates downward
            self.angle = max(self.config.max_downward_angle, self.angle - self.config.downward_rotation_speed * 2)
        else:
            if self.velocity < 0:  # Moving upward
                self.angle = self.config.max_upward_angle
            else:  # Falling
                self.angle = max(self.config.max_downward_angle, self.angle - self.config.downward_rotation_speed)
                
    def get_rect(self):
        """Get the collision rectangle for the bird."""
        # Rotate the current image
        rotated_bird = pygame.transform.rotate(self.current_img, self.angle)
        
        # Get the rect of the rotated image
        rect = rotated_bird.get_rect(center=(self.x + self.midflap_img.get_width()//2, 
                                           self.y + self.midflap_img.get_height()//2))
                                           
        # Create a smaller collision rect for more accurate detection
        inset = int(rect.width * 0.1)  # 10% inset
        collision_rect = pygame.Rect(
            rect.x + inset,
            rect.y + inset,
            rect.width - (inset * 2),
            rect.height - (inset * 2)
        )
        
        return collision_rect, rect
        
    def draw(self, surface):
        """Draw the bird with current rotation."""
        # Rotate the current image
        rotated_bird = pygame.transform.rotate(self.current_img, self.angle)
        
        # Get the rect of the rotated image
        rect = rotated_bird.get_rect(center=(self.x + self.midflap_img.get_width()//2, 
                                           self.y + self.midflap_img.get_height()//2))
                                           
        # Draw the rotated bird
        surface.blit(rotated_bird, rect.topleft)


class PipeManager:
    """Manages pipe obstacles, generation, movement and collision detection."""
    
    def __init__(self, assets, config, screen_width, screen_height):
        """Initialize pipe manager."""
        self.assets = assets
        self.config = config
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.land_height = int(screen_height * 0.17)
        
        # Pipe variables
        self.pipes = []
        self.pipe_gap = int(screen_height * 0.17)  # Gap between pipes
        self.pipe_frequency = 3000  # New pipe every 3 seconds
        self.last_pipe = pygame.time.get_ticks() - self.pipe_frequency  # Time since last pipe
        
        # Load pipe images
        self.load_images()
        
    def load_images(self):
        """Load pipe images based on theme."""
        # Choose pipe image based on theme
        pipe_filename = 'pipe-red.png' if self.config.is_night_theme else 'greenpipe.png'
        
        # Load pipe image
        self.pipe_img = self.assets.load_image(pipe_filename, 'greenpipe.png')
        
        # Scale pipe image
        pipe_width = int(self.screen_width * 0.15)  # 15% of screen width
        pipe_height = int(self.pipe_img.get_height() * (pipe_width / self.pipe_img.get_width()))
        self.pipe_img = pygame.transform.scale(self.pipe_img, (pipe_width, pipe_height))
        
        # Create top pipe by rotating the bottom pipe
        self.pipe_top_img = pygame.transform.rotate(self.pipe_img, 180)
        self.pipe_bottom_img = self.pipe_img
        
    def generate_pipe(self):
        """Generate a new pipe with random gap position."""
        # Position the pipe beyond the right edge of the screen
        pipe_x = self.screen_width
        
        # Calculate boundaries for the gap position
        usable_height = self.screen_height - self.land_height
        
        # Ensure the gap is never too close to the top or bottom
        min_gap_y = int(usable_height * 0.25)
        max_gap_y = int(usable_height * 0.75)
        
        # Center of the gap
        gap_y = random.randint(min_gap_y, max_gap_y)
        
        return [pipe_x, gap_y]
        
    def update(self, dt, game_state):
        """Update pipe positions and generate new pipes."""
        if game_state != 1:  # Only move pipes in PLAYING state
            return 0  # No score increase
            
        score_increase = 0
        
        # Generate new pipes on a timer
        time_now = pygame.time.get_ticks()
        if time_now - self.last_pipe > self.pipe_frequency:
            self.pipes.append(self.generate_pipe())
            self.last_pipe = time_now
            
        # Update pipe positions and handle removal
        pipe_removal = []
        for pipe_index, pipe in enumerate(self.pipes):
            # Move pipe to the left
            pipe[0] -= self.config.scroll_speed
            
            # Score when pipe passes the middle of the screen
            pipe_center = pipe[0] + (self.pipe_top_img.get_width() / 2)
            if pipe_center <= self.screen_width / 2 and pipe_center > (self.screen_width / 2) - self.config.scroll_speed:
                score_increase = 1
                
            # Remove pipes that have moved off the left edge
            if pipe[0] < -self.pipe_top_img.get_width():
                pipe_removal.append(pipe_index)
                
        # Remove off-screen pipes
        for index in sorted(pipe_removal, reverse=True):
            self.pipes.pop(index)
            
        return score_increase
        
    def check_collision(self, bird_rect):
        """Check if the bird collides with any pipes."""
        for pipe in self.pipes:
            # Calculate gap position
            gap_center_y = pipe[1]
            half_gap = self.pipe_gap // 2
            
            # Top pipe position
            top_pipe_y = gap_center_y - half_gap - self.pipe_top_img.get_height()
            
            # Create more precise collision rect for top pipe
            pipe_width = self.pipe_top_img.get_width()
            inset_x = int(pipe_width * 0.05)
            top_pipe_rect = pygame.Rect(
                pipe[0] + inset_x, 
                top_pipe_y, 
                pipe_width - (inset_x * 2), 
                self.pipe_top_img.get_height()
            )
            
            # Bottom pipe position
            bottom_pipe_y = gap_center_y + half_gap
            bottom_pipe_rect = pygame.Rect(
                pipe[0] + inset_x, 
                bottom_pipe_y, 
                pipe_width - (inset_x * 2), 
                self.pipe_bottom_img.get_height()
            )
            
            # Check for collision
            if bird_rect.colliderect(top_pipe_rect) or bird_rect.colliderect(bottom_pipe_rect):
                return True
                
        return False
        
    def draw(self, surface):
        """Draw all active pipes."""
        for pipe in self.pipes:
            # Calculate gap position
            gap_center_y = pipe[1]
            half_gap = self.pipe_gap // 2
            
            # Top pipe
            top_pipe_y = gap_center_y - half_gap - self.pipe_top_img.get_height()
            surface.blit(self.pipe_top_img, (pipe[0], top_pipe_y))
            
            # Bottom pipe
            bottom_pipe_y = gap_center_y + half_gap
            surface.blit(self.pipe_bottom_img, (pipe[0], bottom_pipe_y))


class ScoreDisplay:
    """Manages score display and related UI elements."""
    
    def __init__(self, assets, screen_width, screen_height):
        """Initialize score display."""
        self.assets = assets
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Load number images
        self.number_images = {}
        self.load_number_images()
        
        # Game over image
        self.load_gameover_image()
        
    def load_number_images(self):
        """Load images for digits 0-9."""
        for i in range(10):
            self.number_images[i] = self.assets.load_image(f'{i}.png')
            
            # If no image was found, create a text rendering as fallback
            if self.number_images[i].get_width() <= 2:
                font = pygame.font.SysFont(None, 40)
                self.number_images[i] = font.render(str(i), True, (255, 255, 255))
        
        # Scale all number images
        digit_height = int(self.screen_height * 0.08)
        for i in range(10):
            original_ratio = self.number_images[i].get_width() / self.number_images[i].get_height()
            digit_width = int(digit_height * original_ratio)
            self.number_images[i] = pygame.transform.scale(self.number_images[i], (digit_width, digit_height))
    
    def load_gameover_image(self):
        """Load and scale game over image."""
        self.gameover_img = self.assets.load_image('gameover.png')
        
        # Scale the game over image
        gameover_width = int(self.screen_width * 0.5)  # 50% of screen width
        gameover_height = int(gameover_width * self.gameover_img.get_height() / self.gameover_img.get_width())
        self.gameover_img = pygame.transform.scale(self.gameover_img, (gameover_width, gameover_height))
    
    def draw_score(self, surface, score):
        """Draw the current score on screen."""
        # Convert score to string to get individual digits
        score_str = str(score)
        
        # Calculate total width of all digits to center
        total_width = sum(self.number_images[int(digit)].get_width() for digit in score_str)
        
        # Position the score in the upper part of the screen
        x_pos = (self.screen_width - total_width) // 2
        y_pos = int(self.screen_height * 0.03)
        
        # Draw each digit
        for digit in score_str:
            digit_img = self.number_images[int(digit)]
            surface.blit(digit_img, (x_pos, y_pos))
            x_pos += digit_img.get_width()
            
    def draw_gameover(self, surface):
        """Draw the game over image."""
        x = (self.screen_width - self.gameover_img.get_width()) // 2
        y = (self.screen_height - self.gameover_img.get_height()) // 2
        surface.blit(self.gameover_img, (x, y))


class GameStateManager:
    """Manages game states and transitions."""
    
    # Game state constants
    START = 0
    PLAYING = 1
    GAME_OVER = 2
    RESTART = 3
    
    def __init__(self):
        """Initialize game state manager."""
        self.state = self.START
        self.gameover_time = 0
        
    def handle_event(self, event, bird, sounds):
        """Handle input events based on current game state."""
        if event.type == pygame.QUIT:
            return False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
                
            elif event.key == pygame.K_SPACE:
                if self.state == self.START:
                    self.state = self.PLAYING
                    bird.jump()
                    sounds['wing'].play()
                elif self.state == self.PLAYING:
                    bird.jump()
                    sounds['wing'].play()
                elif self.state == self.GAME_OVER:
                    # Move to restart state when spacebar is pressed in game over state
                    self.state = self.RESTART
                    
        elif event.type == pygame.FINGERDOWN:
            if self.state == self.START:
                self.state = self.PLAYING
                bird.jump()
                sounds['wing'].play()
            elif self.state == self.PLAYING:
                bird.jump()
                sounds['wing'].play()
            elif self.state == self.GAME_OVER:
                # Move to restart state when screen is tapped in game over state
                self.state = self.RESTART
                
        return True
        
    def update(self, current_time):
        """Update game state logic."""
        # Remove automatic timer transition
        # Game over state will stay until player input
        if self.state == self.GAME_OVER:
            if self.gameover_time == 0:
                self.gameover_time = current_time
            # Removed the automatic transition after 2 seconds
                
    def set_gameover(self):
        """Set the game to game over state."""
        self.state = self.GAME_OVER
        self.gameover_time = 0
        
    def reset(self):
        """Reset the game state."""
        self.state = self.START
        self.gameover_time = 0


class FlashEffect:
    """Manages visual flash effects."""
    
    def __init__(self, screen_width, screen_height):
        """Initialize flash effect."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        self.alpha = 0
        self.duration = 100  # Flash duration in milliseconds
        self.start_time = 0
        
    def start_flash(self, current_time):
        """Start the flash effect."""
        self.alpha = 180  # Semi-transparent white
        self.start_time = current_time
        
    def update(self, current_time):
        """Update flash alpha based on elapsed time."""
        if self.alpha > 0:
            flash_elapsed = current_time - self.start_time
            if flash_elapsed < self.duration:
                # Flash is still active
                pass
            else:
                # Flash effect is over
                self.alpha = 0
                
    def draw(self, surface):
        """Draw the flash effect if active."""
        if self.alpha > 0:
            self.surface.fill((255, 255, 255, self.alpha))
            surface.blit(self.surface, (0, 0))


class FlappyGame:
    """Main game class that coordinates all components."""
    
    def __init__(self):
        """Initialize the game."""
        # Initialize pygame
        pygame.init()
        pygame.mixer.init()
        
        # Set up environment variables for Android
        os.environ['SDL_ANDROID_HIDE_KEYBOARD'] = '1'
        os.environ['SDL_ANDROID_IMMERSIVE_MODE'] = '1'
        
        # Get screen dimensions
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h
        
        # Adjust screen width if too wide
        if self.screen_width / self.screen_height > 1.2:
            self.screen_width = 412
            
        # Set up display
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), 
                                             pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption('Flappy Bird')
        pygame.key.set_repeat(0)  # Disable key repeat
        
        # Game area dimensions
        self.game_area_height = int(self.screen_height * 0.78)
        self.game_area_y_offset = int(self.screen_height * 0.11)
        self.game_surface = pygame.Surface((self.screen_width, self.game_area_height))
        
        # Initialize core components
        self.assets = GameAssetManager()
        self.config = GameConfig(is_night_theme=True)
        self.load_sounds()
        
        # Initialize game objects
        self.background = BackgroundManager(self.assets, self.config, self.screen_width, self.game_area_height)
        self.bird = Bird(self.assets, self.config, self.screen_width, self.game_area_height)
        self.pipes = PipeManager(self.assets, self.config, self.screen_width, self.game_area_height)
        self.score_display = ScoreDisplay(self.assets, self.screen_width, self.game_area_height)
        self.flash = FlashEffect(self.screen_width, self.game_area_height)
        
        # Game state and scoring
        self.state_manager = GameStateManager()
        self.score = 0
        self.die_sound_played = False
        
        # Clock for controlling framerate
        self.clock = pygame.time.Clock()
        
        # To ensure consistent performance between themes, add frame timing code
        self.frame_times = []
        self.last_fps_update = 0
        self.fps = 0
        
    def load_sounds(self):
        """Load all game sounds."""
        self.sounds = {
            'point': self.assets.load_sound('point.ogg', 0.7, 'point.wav'),
            'hit': self.assets.load_sound('hit.wav', 1.0, 'hit.ogg'),
            'die': self.assets.load_sound('die.wav', 1.0),
            'wing': self.assets.load_sound('wing.ogg', 0.7, 'wing.wav')
        }
        
    def reset_game(self):
        """Reset the game after game over."""
        # Toggle theme
        self.config.toggle_theme()
        
        # Reload assets for new theme
        self.background.load_assets()
        self.bird.load_images()
        self.pipes.load_images()
        
        # Reset objects
        self.bird.reset_position()
        self.pipes.pipes = []
        
        # Reset state and score
        self.state_manager.reset()
        self.score = 0
        self.die_sound_played = False
        
    def handle_events(self):
        """Process all game events."""
        for event in pygame.event.get():
            if not self.state_manager.handle_event(event, self.bird, self.sounds):
                return False
        return True
        
    def update(self):
        """Update game state."""
        current_time = pygame.time.get_ticks()
        
        # Update state manager
        self.state_manager.update(current_time)
        
        # Handle state transitions
        if self.state_manager.state == GameStateManager.RESTART:
            self.reset_game()
            
        # Update game objects
        self.background.update(1, self.state_manager.state)
        self.bird.update_animation(current_time)
        self.bird.update(1, self.state_manager.state)
        
        # Update flash effect
        self.flash.update(current_time)
        
        # Get bird collision rect - moved outside the PLAYING state check
        bird_collision_rect, _ = self.bird.get_rect()
        
        # Check collision with land - moved outside the PLAYING state check
        ground_collision, land_y = self.background.check_land_collision(self.bird)
        if ground_collision:
            if self.state_manager.state != GameStateManager.GAME_OVER:
                self.sounds['hit'].play()
                self.sounds['die'].play()
                self.state_manager.set_gameover()
                self.die_sound_played = True
            # Position bird on top of the land
            self.bird.y = land_y - self.bird.midflap_img.get_height()
            self.bird.velocity = 0
        
        # Game logic when playing
        if self.state_manager.state == GameStateManager.PLAYING:
            # Update pipes and check for score increase
            score_increase = self.pipes.update(1, self.state_manager.state)
            if score_increase > 0:
                self.score += score_increase
                self.sounds['point'].play()
            
            # Check collision with pipes
            pipe_collision = self.pipes.check_collision(bird_collision_rect)
            
            # Check collision with ceiling
            ceiling_collision = self.bird.y < 0
            
            # Handle collisions
            if pipe_collision and self.state_manager.state != GameStateManager.GAME_OVER:
                self.sounds['hit'].play()
                self.sounds['die'].play()
                self.state_manager.set_gameover()
                self.die_sound_played = True
                self.flash.start_flash(current_time)
                
            if ceiling_collision:
                self.bird.y = 0
                self.bird.velocity = 0
                
    def draw(self):
        """Draw the game."""
        # Fill game surface with black
        self.game_surface.fill((0, 0, 0))
        
        # Draw background
        self.background.draw(self.game_surface)
        
        # Draw objects based on game state
        if self.state_manager.state == GameStateManager.START:
            # Draw bird and tap to start
            self.bird.draw(self.game_surface)
            # Add land drawing here
            self.background.draw_land(self.game_surface)
            self.background.draw_tap_to_start(self.game_surface)
            self.score_display.draw_score(self.game_surface, 0)
            
        else:
            # Draw pipes
            self.pipes.draw(self.game_surface)
            
            # Draw bird
            self.bird.draw(self.game_surface)
            
            # Add land drawing here
            self.background.draw_land(self.game_surface)
            
            # Draw score
            self.score_display.draw_score(self.game_surface, self.score)
            
            # Draw game over in GAME_OVER state
            if self.state_manager.state == GameStateManager.GAME_OVER:
                self.score_display.draw_gameover(self.game_surface)
                
        # Draw flash effect
        self.flash.draw(self.game_surface)
        
        # Debug: Uncomment to display FPS
        # fps_text = f"FPS: {self.fps}"
        # font = pygame.font.SysFont(None, 24)
        # fps_surface = font.render(fps_text, True, (255, 255, 255))
        # self.game_surface.blit(fps_surface, (10, 10))
        
        # Fill the screen with black first
        self.screen.fill((0, 0, 0))
        
        # Draw the game surface onto the main screen
        self.screen.blit(self.game_surface, (0, self.game_area_y_offset))
        
        # Update display
        pygame.display.flip()
        
    def run(self):
        """Main game loop."""
        running = True
        while running:
            # Time the frame
            frame_start = pygame.time.get_ticks()
            
            # Handle events
            running = self.handle_events()
            
            # Update game state
            self.update()
            
            # Draw the game
            self.draw()
            
            # Cap the frame rate
            self.clock.tick(60)
            
            # Calculate FPS
            frame_time = pygame.time.get_ticks() - frame_start
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 30:
                self.frame_times.pop(0)
            
            if pygame.time.get_ticks() - self.last_fps_update > 1000:
                self.fps = int(1000 / (sum(self.frame_times) / len(self.frame_times)))
                self.last_fps_update = pygame.time.get_ticks()
            
        # Clean up
        pygame.quit()


# Create and run the game
if __name__ == "__main__":
    game = FlappyGame()
    game.run()