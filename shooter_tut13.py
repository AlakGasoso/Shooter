import pygame
from pygame import mixer
import os
import random
import csv
import button

mixer.init()
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = int(SCREEN_WIDTH * 0.8)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Shooter')

# set framerate
clock = pygame.time.Clock()
FPS = 60


# AJUSTES DE DIFICULDADE

PLAYER_SPEED = 6            # mais rápido (antes 5)
PLAYER_JUMP_VEL = -13       # pulo mais alto (antes -11)
PLAYER_BULLET_DMG = 25
ENEMY_PROJECTILE_DMG = 10   # dano da fireball no jogador
ENEMY_SHOOT_COOLDOWN = 40   # intervalo entre tiros do inimigo

# variaveis
GRAVITY = 0.75
SCROLL_THRESH = 200
ROWS = 16
COLS = 150
TILE_SIZE = SCREEN_HEIGHT // ROWS
TILE_TYPES = 21
MAX_LEVELS = 3
screen_scroll = 0
bg_scroll = 0
level = 1
start_game = False
start_intro = False

# variaveis do jogador
moving_left = False
moving_right = False
shoot = False
grenade = False
grenade_thrown = False

# som
jump_fx = pygame.mixer.Sound('audio/jump.wav');    jump_fx.set_volume(0.05)
shot_fx = pygame.mixer.Sound('audio/shot.wav');    shot_fx.set_volume(0.05)
grenade_fx = pygame.mixer.Sound('audio/grenade.wav'); grenade_fx.set_volume(0.05)


# IMAGENS 

# Botões do menu
start_img = pygame.image.load('img/start_btn.png').convert_alpha()
exit_img = pygame.image.load('img/exit_btn.png').convert_alpha()
restart_img = pygame.image.load('img/restart_btn.png').convert_alpha()

# FUNDO 
if os.path.exists('img/background/cenário/cidade.png'):
    cidade_img = pygame.image.load('img/background/cenário/cidade.png').convert_alpha()
elif os.path.exists('img/Background/cidade.png'):
    cidade_img = pygame.image.load('img/Background/cidade.png').convert_alpha()
else:
    cidade_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# Helpers de cor para tiles
def recolor_mask(surface, color):
  
    img = surface.copy()
    # zera RGB mantendo alpha
    mul = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    mul.fill((0, 0, 0, 255))
    img.blit(mul, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    # adiciona a cor desejada
    add = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    add.fill((color[0], color[1], color[2], 0))
    img.blit(add, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return img

def darken(surface, factor=0.55):
    img = surface.copy()
    shade = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    shade.fill((int(255*factor), int(255*factor), int(255*factor), 255))
    img.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return img

# Tiles (mapa) + ajustes visuais
img_list = []
for x in range(TILE_TYPES):
    raw = pygame.image.load(f'img/Tile/{x}.png').convert_alpha()
    img = pygame.transform.scale(raw, (TILE_SIZE, TILE_SIZE))
    # chão
    if 0 <= x <= 8:
        img = darken(img, 0.55)
    # LAVA 
    if 9 <= x <= 10:
        img = recolor_mask(img, (230, 40, 0))
    img_list.append(img)

# Ícones/Projéteis/Itens (padronizar tamanhos)
bullet_img = pygame.image.load('img/icons/bullet.png').convert_alpha()
grenade_img = pygame.image.load('img/icons/grenade.png').convert_alpha()
health_box_img = pygame.image.load('img/icons/health_box.png').convert_alpha()
ammo_box_img = pygame.image.load('img/icons/ammo_box.png').convert_alpha()
grenade_box_img = pygame.image.load('img/icons/grenade_box.png').convert_alpha()

# tamanhos padronizados
BULLET_SIZE  = (10, 10)                       # projétil pequeno
GRENADE_SIZE = (int(TILE_SIZE * 0.5),) * 2    # granada ~ metade do tile
BOX_SIZE     = (TILE_SIZE, TILE_SIZE)         # cada caixa ocupa 1 tile

bullet_img  = pygame.transform.scale(bullet_img,  BULLET_SIZE)
grenade_img = pygame.transform.scale(grenade_img, GRENADE_SIZE)
health_box_img  = pygame.transform.scale(health_box_img,  BOX_SIZE)
ammo_box_img    = pygame.transform.scale(ammo_box_img,    BOX_SIZE)
grenade_box_img = pygame.transform.scale(grenade_box_img, BOX_SIZE)

# Fireball (inimigos) 
FIREBALL_SIZE = (int(TILE_SIZE*0.45), int(TILE_SIZE*0.45))
if os.path.exists('img/icons/fireball.png'):
    fireball_img = pygame.image.load('img/icons/fireball.png').convert_alpha()
    fireball_img = pygame.transform.scale(fireball_img, FIREBALL_SIZE)
else:
    fireball_img = pygame.Surface(FIREBALL_SIZE, pygame.SRCALPHA)
    r = FIREBALL_SIZE[0]//2
    pygame.draw.circle(fireball_img, (255,120,0), (r,r), r)
    pygame.draw.circle(fireball_img, (255,200,50), (r,r), int(r*0.6))

item_boxes = {'Health':health_box_img,'Ammo':ammo_box_img,'Grenade':grenade_box_img}

# define cores
BG    = (90, 120, 95)   # fundo base mais escuro
RED   = (255, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
PINK  = (235, 65, 54)

# def font
font = pygame.font.SysFont('Futura', 30)

def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))

def draw_bg():
    screen.fill(BG)
    width = cidade_img.get_width()
    height = cidade_img.get_height()
    y = SCREEN_HEIGHT - height
    tiles = (SCREEN_WIDTH // width) + 3
    for i in range(tiles):
        screen.blit(cidade_img, ((i * width) - bg_scroll * 0.6, y))

# animações 
ANIM_COOLDOWNS = {'Idle':150, 'Run':90, 'Jump':120, 'Death':100, 'Attack':80}

def load_anim_frames(char_type, anim_name, scale):
    folder = os.path.join('img', char_type, anim_name)
    frames = []
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith('.png'):
                img = pygame.image.load(os.path.join(folder, fname)).convert_alpha()
                img = pygame.transform.scale(img, (int(img.get_width()*scale),
                                                   int(img.get_height()*scale)))
                frames.append(img)
    
    return frames

#function to reset level
def reset_level():
    enemy_group.empty()
    bullet_group.empty()
    fireball_group.empty()
    grenade_group.empty()
    explosion_group.empty()
    item_box_group.empty()
    decoration_group.empty()
    water_group.empty()
    exit_group.empty()
    return [[-1]*COLS for _ in range(ROWS)]

class Soldier(pygame.sprite.Sprite):
    def __init__(self, char_type, x, y, scale, speed, ammo, grenades):
        pygame.sprite.Sprite.__init__(self)
        self.alive = True
        self.char_type = char_type
        self.speed = speed
        self.ammo = ammo
        self.start_ammo = ammo
        self.shoot_cooldown = 0
        self.grenades = grenades
        self.health = 100
        self.max_health = self.health
        self.direction = 1
        self.vel_y = 0
        self.jump = False
        self.in_air = True
        self.flip = False

        # animações (inclui Attack se existir pasta)
        base_actions = ['Idle', 'Run', 'Jump', 'Death']
        extra_actions = []
        if load_anim_frames(self.char_type, 'Attack', scale):
            extra_actions.append('Attack')
        self.anim_names = base_actions + extra_actions

        self.animation_list = []
        for name in self.anim_names:
            frames = load_anim_frames(self.char_type, name, scale)
            if not frames:
                # se uma ação base faltar, garante 1 frame vazio
                surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                frames = [surf]
            self.animation_list.append(frames)

        self.index_of = {n:i for i, n in enumerate(self.anim_names)}
        self.has_attack = ('Attack' in self.index_of)

        self.frame_index = 0
        self.action = self.index_of.get('Idle', 0)
        self.update_time = pygame.time.get_ticks()
        self.attack_timer = 0  # controla retorno após anim de ataque

        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.width = self.image.get_width()
        self.height = self.image.get_height()

        # ai
        self.move_counter = 0
        self.vision = pygame.Rect(0, 0, 150, 20)
        self.idling = False
        self.idling_counter = 0

    def update(self):
        self.update_animation()
        self.check_alive()
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
            # quando terminar o tempo de ataque, volta para Idle
            if self.attack_timer == 0 and self.char_type == 'enemy':
                self.update_action(self.index_of.get('Idle', 0))

    def move(self, moving_left, moving_right):
        screen_scroll = 0
        dx = 0
        dy = 0

        if moving_left:
            dx = -self.speed
            self.flip = True
            self.direction = -1
        if moving_right:
            dx = self.speed
            self.flip = False
            self.direction = 1

        if self.jump and not self.in_air:
            self.vel_y = PLAYER_JUMP_VEL
            self.jump = False
            self.in_air = True

        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10
        dy += self.vel_y

        for tile in world.obstacle_list:
            if tile[1].colliderect(self.rect.x + dx, self.rect.y, self.width, self.height):
                dx = 0
                if self.char_type == 'enemy':
                    self.direction *= -1
                    self.move_counter = 0
            if tile[1].colliderect(self.rect.x, self.rect.y + dy, self.width, self.height):
                if self.vel_y < 0:
                    self.vel_y = 0
                    dy = tile[1].bottom - self.rect.top
                else:
                    self.vel_y = 0
                    self.in_air = False
                    dy = tile[1].top - self.rect.bottom

        # lava 
        if pygame.sprite.spritecollide(self, water_group, False):
            self.health = 0

        level_complete = False
        if pygame.sprite.spritecollide(self, exit_group, False):
            level_complete = True

        if self.rect.bottom > SCREEN_HEIGHT:
            self.health = 0

        if self.char_type == 'player':
            if self.rect.left + dx < 0 or self.rect.right + dx > SCREEN_WIDTH:
                dx = 0

        self.rect.x += dx
        self.rect.y += dy

        if self.char_type == 'player':
            if (self.rect.right > SCREEN_WIDTH - SCROLL_THRESH and bg_scroll < (world.level_length * TILE_SIZE) - SCREEN_WIDTH)\
               or (self.rect.left < SCROLL_THRESH and bg_scroll > abs(dx)):
                self.rect.x -= dx
                screen_scroll = -dx

        return screen_scroll, level_complete

    def shoot(self):
        if self.char_type == 'enemy':
            # inimigo: fireball + animação de ataque (se existir)
            if self.shoot_cooldown == 0:
                self.shoot_cooldown = ENEMY_SHOOT_COOLDOWN
                fb = Fireball(self.rect.centerx + (0.6 * self.rect.size[0] * self.direction),
                              self.rect.centery, self.direction)
                fireball_group.add(fb)
                # dispara animação de ataque por um curto período
                if self.has_attack:
                    self.update_action(self.index_of['Attack'])
                    # tempo aproximado: nº de frames * cooldown da ação
                    frames = len(self.animation_list[self.index_of['Attack']])
                    cooldown = ANIM_COOLDOWNS.get('Attack', 80)
                    self.attack_timer = max(10, int(0.8 * frames * (cooldown/16)))  # ~0.8 ciclo
                else:
                    # fallback: dá um "pisca" no Run por pouco tempo
                    self.update_action(self.index_of.get('Run', 0))
                    self.attack_timer = 12
        else:
            # player: bala comum
            if self.shoot_cooldown == 0 and self.ammo > 0:
                self.shoot_cooldown = 20
                bullet = Bullet(self.rect.centerx + (0.75 * self.rect.size[0] * self.direction), self.rect.centery, self.direction)
                bullet_group.add(bullet)
                self.ammo -= 1
                shot_fx.play()

    def ai(self):
        if self.alive and player.alive:
            if not self.idling and random.randint(1, 200) == 1:
                self.update_action(self.index_of.get('Idle', 0))
                self.idling = True
                self.idling_counter = 50
            if self.vision.colliderect(player.rect):
                # se estiver em ataque, não muda; senão atira
                if self.attack_timer == 0:
                    self.update_action(self.index_of.get('Idle', 0))
                    self.shoot()
            else:
                if not self.idling:
                    ai_moving_right = self.direction == 1
                    ai_moving_left = not ai_moving_right
                    self.move(ai_moving_left, ai_moving_right)
                    # só troca ação se não estiver no ataque
                    if self.attack_timer == 0:
                        self.update_action(self.index_of.get('Run', 0))
                    self.move_counter += 1
                    self.vision.center = (self.rect.centerx + 75 * self.direction, self.rect.centery)
                    if self.move_counter > TILE_SIZE:
                        self.direction *= -1
                        self.move_counter *= -1
                else:
                    self.idling_counter -= 1
                    if self.idling_counter <= 0:
                        self.idling = False

        self.rect.x += screen_scroll

    def update_animation(self):
        # pega cooldown da ação atual
        
        curr_name = self.anim_names[self.action]
        cooldown = ANIM_COOLDOWNS.get(curr_name, 100)

        frames = self.animation_list[self.action]
        self.image = frames[self.frame_index]

        # avança frame (se tiver >1)
        if len(frames) > 1 and pygame.time.get_ticks() - self.update_time > cooldown:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1

        # loop ou travar na morte
        if self.frame_index >= len(frames):
            if curr_name == 'Death':
                self.frame_index = len(frames) - 1
            else:
                self.frame_index = 0

    def update_action(self, new_action_idx):
        if new_action_idx != self.action:
            self.action = new_action_idx
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def check_alive(self):
        if self.health <= 0:
            self.health = 0
            self.speed = 0
            self.alive = False
            self.update_action(self.index_of.get('Death', 0))

    def draw(self):
        screen.blit(pygame.transform.flip(self.image, self.flip, False), self.rect)

class World():
    def __init__(self):
        self.obstacle_list = []

    def process_data(self, data):
        self.level_length = len(data[0])
        for y, row in enumerate(data):
            for x, tile in enumerate(row):
                if tile >= 0:
                    img = img_list[tile]
                    img_rect = img.get_rect()
                    img_rect.x = x * TILE_SIZE
                    img_rect.y = y * TILE_SIZE
                    tile_data = (img, img_rect)
                    if tile >= 0 and tile <= 8:
                        self.obstacle_list.append(tile_data)
                    elif tile >= 9 and tile <= 10:
                        water = Water(img, x * TILE_SIZE, y * TILE_SIZE)   # agora é lava
                        water_group.add(water)
                    elif tile >= 11 and tile <= 14:
                        decoration = Decoration(img, x * TILE_SIZE, y * TILE_SIZE)
                        decoration_group.add(decoration)
                    elif tile == 15:  # player
                        player = Soldier('player', x * TILE_SIZE, y * TILE_SIZE, 1.65, PLAYER_SPEED, 20, 5)
                        health_bar = HealthBar(10, 10, player.health, player.health)
                    elif tile == 16:  # enemy
                        enemy = Soldier('enemy', x * TILE_SIZE, y * TILE_SIZE, 1.65, 2, 20, 0)
                        enemy_group.add(enemy)
                    elif tile == 17:  # ammo box
                        item_box = ItemBox('Ammo', x * TILE_SIZE, y * TILE_SIZE)
                        item_box_group.add(item_box)
                    elif tile == 18:  # grenade box
                        item_box = ItemBox('Grenade', x * TILE_SIZE, y * TILE_SIZE)
                        item_box_group.add(item_box)
                    elif tile == 19:  # health box
                        item_box = ItemBox('Health', x * TILE_SIZE, y * TILE_SIZE)
                        item_box_group.add(item_box)
                    elif tile == 20:  # exit
                        exit = Exit(img, x * TILE_SIZE, y * TILE_SIZE)
                        exit_group.add(exit)

        return player, health_bar

    def draw(self):
        for tile in self.obstacle_list:
            tile[1][0] += screen_scroll
            screen.blit(tile[0], tile[1])

# Objetos de cenário
class Decoration(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
    def update(self):
        self.rect.x += screen_scroll

class Water(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
    def update(self):
        self.rect.x += screen_scroll

class Exit(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
    def update(self):
        self.rect.x += screen_scroll

class ItemBox(pygame.sprite.Sprite):
    def __init__(self, item_type, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.item_type = item_type
        self.image = item_boxes[self.item_type]   # já escalada pra 1 tile
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
    def update(self):
        self.rect.x += screen_scroll
        if pygame.sprite.collide_rect(self, player):
            if self.item_type == 'Health':
                player.health += 25
                if player.health > player.max_health:
                    player.health = player.max_health
            elif self.item_type == 'Ammo':
                player.ammo += 15
            elif self.item_type == 'Grenade':
                player.grenades += 3
            self.kill()

class HealthBar():
    def __init__(self, x, y, health, max_health):
        self.x = x
        self.y = y
        self.health = health
        self.max_health = max_health
    def draw(self, health):
        self.health = health
        ratio = self.health / self.max_health
        pygame.draw.rect(screen, BLACK, (self.x - 2, self.y - 2, 154, 24))
        pygame.draw.rect(screen, RED, (self.x, self.y, 150, 20))
        pygame.draw.rect(screen, GREEN, (self.x, self.y, int(150 * ratio), 20))

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        pygame.sprite.Sprite.__init__(self)
        self.speed = 10
        self.image = bullet_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction
    def update(self):
        self.rect.x += (self.direction * self.speed) + screen_scroll
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        for tile in world.obstacle_list:
            if tile[1].colliderect(self.rect):
                self.kill()
        if pygame.sprite.spritecollide(player, bullet_group, False):
            if player.alive:
                player.health -= 5
                self.kill()
        for enemy in enemy_group:
            if pygame.sprite.spritecollide(enemy, bullet_group, False):
                if enemy.alive:
                    enemy.health -= PLAYER_BULLET_DMG
                    self.kill()

class Fireball(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        pygame.sprite.Sprite.__init__(self)
        self.speed = 7
        self.image = fireball_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.direction = direction
        self.life = 180  # ~3s
    def update(self):
        self.rect.x += (self.direction * self.speed) + screen_scroll
        self.life -= 1
        for tile in world.obstacle_list:
            if tile[1].colliderect(self.rect):
                self.kill(); return
        if pygame.sprite.spritecollide(player, fireball_group, False):
            if player.alive:
                player.health -= ENEMY_PROJECTILE_DMG
                self.kill(); return
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or self.life <= 0:
            self.kill()

class Grenade(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        pygame.sprite.Sprite.__init__(self)
        self.timer = 100
        self.vel_y = -11
        self.speed = 7
        self.image = grenade_img
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        self.direction = direction
    def update(self):
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10
        dx = self.direction * self.speed
        dy = self.vel_y
        for tile in world.obstacle_list:
            if tile[1].colliderect(self.rect.x + dx, self.rect.y, self.width, self.height):
                self.direction *= -1
                dx = self.direction * self.speed
            if tile[1].colliderect(self.rect.x, self.rect.y + dy, self.width, self.height):
                self.speed = 0
                if self.vel_y < 0:
                    self.vel_y = 0
                    dy = tile[1].bottom - self.rect.top
                else:
                    self.vel_y = 0
                    dy = tile[1].top - self.rect.bottom
        self.rect.x += dx + screen_scroll
        self.rect.y += dy
        self.timer -= 1
        if self.timer <= 0:
            self.kill()
            grenade_fx.play()
            explosion = Explosion(self.rect.x, self.rect.y, 0.5)
            explosion_group.add(explosion)
            if abs(self.rect.centerx - player.rect.centerx) < TILE_SIZE * 2 and \
               abs(self.rect.centery - player.rect.centery) < TILE_SIZE * 2:
                player.health -= 50
            for enemy in enemy_group:
                if abs(self.rect.centerx - enemy.rect.centerx) < TILE_SIZE * 2 and \
                   abs(self.rect.centery - enemy.rect.centery) < TILE_SIZE * 2:
                    enemy.health -= 50

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, scale):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        for num in range(1, 6):
            img = pygame.image.load(f'img/explosion/exp{num}.png').convert_alpha()
            img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            self.images.append(img)
        self.frame_index = 0
        self.image = self.images[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.counter = 0
    def update(self):
        self.rect.x += screen_scroll
        EXPLOSION_SPEED = 4
        self.counter += 1
        if self.counter >= EXPLOSION_SPEED:
            self.counter = 0
            self.frame_index += 1
            if self.frame_index >= len(self.images):
                self.kill()
            else:
                self.image = self.images[self.frame_index]

class ScreenFade():
    def __init__(self, direction, colour, speed):
        self.direction = direction
        self.colour = colour
        self.speed = speed
        self.fade_counter = 0
    def fade(self):
        fade_complete = False
        self.fade_counter += self.speed
        if self.direction == 1:
            pygame.draw.rect(screen, self.colour, (0 - self.fade_counter, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.colour, (SCREEN_WIDTH // 2 + self.fade_counter, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.draw.rect(screen, self.colour, (0, 0 - self.fade_counter, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
            pygame.draw.rect(screen, self.colour, (0, SCREEN_HEIGHT // 2 + self.fade_counter, SCREEN_WIDTH, SCREEN_HEIGHT))
        if self.direction == 2:
            pygame.draw.rect(screen, self.colour, (0, 0, SCREEN_WIDTH, 0 + self.fade_counter))
        if self.fade_counter >= SCREEN_WIDTH:
            fade_complete = True
        return fade_complete

# fades
intro_fade = ScreenFade(1, BLACK, 4)
death_fade = ScreenFade(2, PINK, 4)

# buttons
start_button = button.Button(SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2 - 150, start_img, 1)
exit_button = button.Button(SCREEN_WIDTH // 2 - 110, SCREEN_HEIGHT // 2 + 50, exit_img, 1)
restart_button = button.Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 50, restart_img, 2)

# sprite groups
enemy_group = pygame.sprite.Group()
bullet_group = pygame.sprite.Group()
fireball_group = pygame.sprite.Group()
grenade_group = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()
item_box_group = pygame.sprite.Group()
decoration_group = pygame.sprite.Group()
water_group = pygame.sprite.Group()
exit_group = pygame.sprite.Group()

# world data
world_data = [[-1]*COLS for _ in range(ROWS)]
with open(f'level{level}_data.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for x, row in enumerate(reader):
        for y, tile in enumerate(row):
            world_data[x][y] = int(tile)
world = World()
player, health_bar = world.process_data(world_data)

run = True
while run:

    clock.tick(FPS)

    if not start_game:
        screen.fill(BG)
        if start_button.draw(screen):
            start_game = True
            start_intro = True
        if exit_button.draw(screen):
            run = False
    else:
        draw_bg()
        world.draw()
        health_bar.draw(player.health)
        draw_text('AMMO: ', font, WHITE, 10, 35)
        for x in range(player.ammo):
            screen.blit(bullet_img, (90 + (x * 10), 40))
        draw_text('GRENADES: ', font, WHITE, 10, 60)
        for x in range(player.grenades):
            screen.blit(grenade_img, (135 + (x * 15), 60))

        player.update()
        player.draw()

        for enemy in enemy_group:
            enemy.ai()
            enemy.update()
            enemy.draw()

        bullet_group.update()
        fireball_group.update()
        grenade_group.update()
        explosion_group.update()
        item_box_group.update()
        decoration_group.update()
        water_group.update()
        exit_group.update()
        bullet_group.draw(screen)
        fireball_group.draw(screen)
        grenade_group.draw(screen)
        explosion_group.draw(screen)
        item_box_group.draw(screen)
        decoration_group.draw(screen)
        water_group.draw(screen)
        exit_group.draw(screen)

        if start_intro:
            if intro_fade.fade():
                start_intro = False
                intro_fade.fade_counter = 0

        if player.alive:
            if shoot:
                player.shoot()
            elif grenade and not grenade_thrown and player.grenades > 0:
                grenade_obj = Grenade(
                    player.rect.centerx + (0.5 * player.rect.size[0] * player.direction),
                    player.rect.top,
                    player.direction
                )
                grenade_group.add(grenade_obj)
                player.grenades -= 1
                grenade_thrown = True
            if player.in_air:
                player.update_action(player.index_of.get('Jump', 0))
            elif moving_left or moving_right:
                player.update_action(player.index_of.get('Run', 0))
            else:
                player.update_action(player.index_of.get('Idle', 0))
            screen_scroll, level_complete = player.move(moving_left, moving_right)
            bg_scroll -= screen_scroll
            if level_complete:
                start_intro = True
                level += 1
                bg_scroll = 0
                world_data = reset_level()
                if level <= MAX_LEVELS:
                    with open(f'level{level}_data.csv', newline='') as csvfile:
                        reader = csv.reader(csvfile, delimiter=',')
                        for x, row in enumerate(reader):
                            for y, tile in enumerate(row):
                                world_data[x][y] = int(tile)
                    world = World()
                    player, health_bar = world.process_data(world_data)
        else:
            screen_scroll = 0
            if death_fade.fade():
                if restart_button.draw(screen):
                    death_fade.fade_counter = 0
                    start_intro = True
                    bg_scroll = 0
                    world_data = reset_level()
                    with open(f'level{level}_data.csv', newline='') as csvfile:
                        reader = csv.reader(csvfile, delimiter=',')
                        for x, row in enumerate(reader):
                            for y, tile in enumerate(row):
                                world_data[x][y] = int(tile)
                    world = World()
                    player, health_bar = world.process_data(world_data)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                moving_left = True
            if event.key == pygame.K_d:
                moving_right = True
            if event.key == pygame.K_SPACE:
                shoot = True
            if event.key == pygame.K_q:
                grenade = True
            if event.key == pygame.K_w and player.alive:
                player.jump = True
                jump_fx.play()
            if event.key == pygame.K_ESCAPE:
                run = False
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                moving_left = False
            if event.key == pygame.K_d:
                moving_right = False
            if event.key == pygame.K_SPACE:
                shoot = False
            if event.key == pygame.K_q:
                grenade = False
                grenade_thrown = False

    pygame.display.update()

pygame.quit()
