"""Velha Arena — Fight : Club | Python 3.10+ / pygame-ce.

Base didática: reescrevam os blocos sinalizados antes dos próprios commits.
Contratos: cenas.handle_event(event), update(dt em segundos), draw(surface);
App.change_scene(name), finish_match(winner 0/1, reason); modelos abaixo.
Referência: https://insper.github.io/DesignDeSoftware/pygame/handout/
"""

# 01. CONSTANTES E RECURSOS ----------------------------------------------------
import argparse
import math
import os
from pathlib import Path
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:
    import pygame
except ImportError:
    raise SystemExit("Instale a dependência: python -m pip install pygame-ce")

WIDTH, HEIGHT, FPS = 1100, 760, 60
ASSETS = Path(__file__).resolve().parent / "assets"
BG, PANEL = (23, 27, 31), (37, 44, 50)
CREAM, TEXT, MUTED = (244, 234, 209), (241, 238, 224), (164, 177, 182)
P1, P2 = (195, 242, 73), (255, 146, 83)
PLAYER_COLORS = (P1, P2)
SYMBOLS = ("67", "Diamante", "Nether", "ChatGPT", "Claude", "Python",
           "Caveira", "Fogo", "Fantasma", "Raposa")
WEAPONS = [
    dict(name="Pistola", cooldown=420, speed=650, damage=1, count=1, spread=0, radius=5, ttl=1.5),
    dict(name="SMG", cooldown=150, speed=710, damage=1, count=1, spread=0, radius=4, ttl=1.2),
    dict(name="Escopeta", cooldown=820, speed=590, damage=1, count=3, spread=28, radius=5, ttl=0.52),
    dict(name="Precisão", cooldown=1050, speed=1200, damage=2, count=1, spread=0, radius=3, ttl=1.5),
    dict(name="Canhão", cooldown=1200, speed=380, damage=2, count=1, spread=0, radius=13, ttl=2.6),
]
SCENES = ("inicio", "ajuda", "simbolos", "tabuleiro", "armas", "arena", "resultado")
RESOURCES = {}



def load_assets():
    """Carrega imagens após criar a janela; retorna caches de imagens e fontes.

    Recursos ausentes usam desenho/fonte de reserva. Nenhum arquivo é gerado
    durante o jogo, e todos os caminhos partem de ASSETS, nunca do terminal.
    """
    resources = {"fonts": {}, "images": {}, "scaled": {}}
    for kind, count in (("simbolo", 10), ("arma", 5)):
        for index in range(count):
            path = ASSETS / "icons" / f"{kind}_{index}.png"
            try:
                resources["images"][kind, index] = pygame.image.load(str(path)).convert_alpha()
            except (OSError, pygame.error):
                resources["images"][kind, index] = None
    return resources


# 02. UI: TEXTOS, BOTÕES E CONTRATO DAS TELAS ----------------------------------
def text(surface, value, size, pos, color=TEXT, center=False, display=False):
    """Cacheia fontes por tamanho/estilo e devolve o retângulo desenhado."""
    key = (size, display)
    if key not in RESOURCES["fonts"]:
        path = ASSETS / "fonts" / ("Display.ttf" if display else "Text.ttf")
        try:
            RESOURCES["fonts"][key] = pygame.font.Font(str(path), size)
        except (OSError, pygame.error):
            RESOURCES["fonts"][key] = pygame.font.Font(None, size)
    rendered = RESOURCES["fonts"][key].render(str(value), True, color)
    rect = rendered.get_rect(center=pos) if center else rendered.get_rect(topleft=pos)
    surface.blit(rendered, rect)
    return rect


def panel(surface, rect, color=PANEL, border=None):
    pygame.draw.rect(surface, color, rect, border_radius=12)
    if border:
        pygame.draw.rect(surface, border, rect, 2, border_radius=12)


def button(surface, label, rect, active=False):
    rect = pygame.Rect(rect)
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    panel(surface, rect, CREAM if active or hovered else PANEL)
    text(surface, label, 20, rect.center, BG if active or hovered else TEXT, True)
    return rect


def clicked(event, rect):
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pygame.Rect(rect).collidepoint(event.pos)


def draw_icon(surface, kind, index, center, size):
    key = (kind, index, size)
    image = RESOURCES["images"].get((kind, index))
    if image is None:
        text(surface, str(index + 1), max(18, size // 2), center, CREAM, True)
        return
    if key not in RESOURCES["scaled"]:
        RESOURCES["scaled"][key] = pygame.transform.smoothscale(image, (size, size))
    surface.blit(RESOURCES["scaled"][key], (center[0] - size // 2, center[1] - size // 2))


def draw_symbol(surface, index, center, size, color):
    pygame.draw.circle(surface, color, center, size // 2, 3)
    draw_icon(surface, "simbolo", index, center, int(size * 0.76))

# Autoria de Rodrigo Bartolo
def draw_health_bar(surface, pos, hp, max_hp, color):
    """Desenha segmentos retangulares de vida."""
    x, y = pos
    for i in range(max_hp):
        rect = pygame.Rect(x + i * 38, y, 32, 16)
        panel(surface, rect, color if i < hp else PANEL, MUTED)

class Scene:
    """Interface comum das sete telas, sem laços de execução próprios.

    handle_event recebe um evento; update recebe segundos; draw recebe uma
    Surface. As telas estáticas herdam update sem alterar o estado.
    """
    title = "VELHA ARENA / FIGHT : CLUB"

    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        """Ponto de extensão: a tela base não possui comandos próprios."""

    def update(self, dt):
        """Ponto de extensão: telas estáticas não atualizam a simulação."""

    def draw(self, surface):
        surface.fill(BG)
        text(surface, "VA /", 28, (40, 29), P1, display=True)
        text(surface, self.title, 18, (130, 37))
        pygame.draw.line(surface, PANEL, (40, 86), (1060, 86), 2)
        text(surface, "LOCAL / 2 JOGADORES", 14, (40, 718), MUTED)
        sound = "M: sem som" if self.app.audio.muted or not self.app.audio.enabled else "M: som"
        text(surface, sound, 14, (937, 718), MUTED)


# 03. SÍMBOLOS ---------------------------------------------------------------
class SymbolScene(Scene):
    title = "01 / ESCOLHA SEU SÍMBOLO"

    def __init__(self, app):
        super().__init__(app)
        self.active, self.message = 0, "Cliquem em um símbolo para escolher."
        self.cards = [pygame.Rect(90 + i % 5 * 188, 265 + i // 5 * 157, 168, 138) for i in range(10)]

    def handle_event(self, event):
        if clicked(event, (90, 166, 430, 60)):
            self.active = 0
        elif clicked(event, (550, 166, 430, 60)):
            self.active = 1
        for index, rect in enumerate(self.cards):
            if clicked(event, rect):
                if index == self.app.state["symbols"][1 - self.active]:
                    self.message = "Esse símbolo já pertence ao outro jogador."
                else:
                    self.app.state["symbols"][self.active] = index
                    self.app.audio.play("select")
                    self.message = "Escolha salva. Alternem as abas ou continuem."
        if clicked(event, (760, 628, 250, 54)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
            self.app.change_scene("tabuleiro")
        elif clicked(event, (90, 628, 210, 54)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.app.change_scene("inicio")

    def sortear_simbolos(jogo, recursos):
        escolhidos = random.sample(range(10), 2)
        jogo["simbolos"] = escolhidos
        tocar(recursos, "select")
    
    def draw(self, surface):
        super().draw(surface)
        text(surface, "DUAS PESSOAS. DOIS SÍMBOLOS.", 32, (90, 110), display=True)
        for player in range(2):
            label = f"J{player + 1} / {SYMBOLS[self.app.state['symbols'][player]]}"
            button(surface, label, (90 + player * 460, 166, 430, 60), self.active == player)
        for index, rect in enumerate(self.cards):
            owners = [i for i, symbol in enumerate(self.app.state["symbols"]) if symbol == index]
            panel(surface, rect, border=PLAYER_COLORS[owners[0]] if owners else None)
            draw_icon(surface, "simbolo", index, (rect.centerx, rect.y + 50), 68)
            text(surface, SYMBOLS[index], 18, (rect.centerx, rect.y + 101), center=True)
            if owners:
                text(surface, f"J{owners[0] + 1}", 14, (rect.x + 10, rect.y + 8), PLAYER_COLORS[owners[0]])
        text(surface, self.message, 16, (90, 588), MUTED)
        button(surface, "Voltar", (90, 628, 210, 54))
        button(surface, "Continuar / Enter", (760, 628, 250, 54), True)


# 04. MENU E AJUDA ------------------------------------------------------------
class MenuScene(Scene):
    def handle_event(self, event):
        enter = event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        if self.app.scene_name == "ajuda":
            if enter or clicked(event, (420, 620, 260, 56)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.app.change_scene("inicio")
        elif enter or clicked(event, (390, 490, 320, 60)):
            self.app.change_scene("simbolos")
        elif clicked(event, (390, 568, 320, 54)):
            self.app.change_scene("ajuda")

    def draw(self, surface):
        super().draw(surface)
        if self.app.scene_name == "ajuda":
            text(surface, "COMO ENTRAR NA BRIGA", 42, (100, 125), display=True)
            lines = ["01 / Façam uma linha de três no tabuleiro para vencer.",
                     "02 / Deu velha? Cada um escolhe e confirma sua arma.",
                     "03 / Na arena, eliminem as três vidas do adversário.",
                     "J1: W A S D para mover / F para atirar.",
                     "J2: Setas para mover / Enter para atirar.",
                     "A mira é automática. Paredes bloqueiam corpos e tiros.",
                     "ESC pausa; H pausado volta ao início. M alterna o som.",
                     "Tabuleiro: cliquem ou usem 1–9, da esquerda para a direita.",
                     "Morte simultânea: novo duelo com 1 vida para cada."]
            for index, line in enumerate(lines):
                text(surface, line, 20, (100, 215 + index * 40), MUTED if index > 5 else TEXT)
            button(surface, "Voltar / Enter", (420, 620, 260, 56), True)
            return
        text(surface, "DO TABULEIRO AO DUELO", 18, (550, 167), P1, True)
        text(surface, "VELHA ARENA", 84, (550, 258), CREAM, True, True)
        text(surface, "FIGHT : CLUB", 42, (550, 338), P2, True, True)
        text(surface, "Vença na estratégia. Desempate na arena.", 22, (550, 415), MUTED, True)
        button(surface, "Iniciar / Enter", (390, 490, 320, 60), True)
        button(surface, "Ajuda", (390, 568, 320, 54))
        text(surface, "RODRIGO / THIAGO / LUCAS", 14, (550, 666), MUTED, True)


# 05. TABULEIRO: MODELO E TELA ------------------------------------------------
class BoardModel:
    """Modelo independente de eventos, desenho e áudio.

    cells usa None/0/1; turn e winner usam índices 0/1, nunca nomes de símbolos.
    winner=None significa que ninguém venceu. draw só vale sem vencedor.
    winning_line guarda a primeira linha vencedora, ou None.
    play retorna False sem mutação quando uma jogada é inválida.
    """
    LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
             (2, 5, 8), (0, 4, 8), (2, 4, 6))

    def __init__(self, start_player=0):
        self.reset(start_player)

    def reset(self, start_player=0):
        """Reinicia somente o tabuleiro; o placar pertence ao App."""
        self.cells, self.turn = [None] * 9, start_player
        self.winner, self.winning_line, self.draw = None, None, False

    def play(self, index):
        """Aplica uma casa 0–8; vitória tem prioridade sobre empate na 9ª."""
        if not 0 <= index < 9 or self.cells[index] is not None or self.winner is not None or self.draw:
            return False
        self.cells[index] = self.turn
        for line in self.LINES:
            if all(self.cells[cell] == self.turn for cell in line):
                self.winner, self.winning_line = self.turn, line
                return True
        self.draw = all(cell is not None for cell in self.cells)
        if not self.draw:
            self.turn = 1 - self.turn
        return True


class BoardScene(Scene):
    title = "02 / TABULEIRO"

    def __init__(self, app):
        super().__init__(app)
        self.model = BoardModel(app.state["starter"])
        self.cells = [pygame.Rect(326 + i % 3 * 150, 207 + i // 3 * 150, 142, 142) for i in range(9)]

    def handle_event(self, event):
        index = next((i for i, rect in enumerate(self.cells) if clicked(event, rect)), None)
        if event.type == pygame.KEYDOWN:
            keys = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                    pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9)
            keypad = (pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4, pygame.K_KP5,
                      pygame.K_KP6, pygame.K_KP7, pygame.K_KP8, pygame.K_KP9)
            if event.key in keys + keypad:
                index = (keys if event.key in keys else keypad).index(event.key)
        if index is not None and self.model.play(index):
            self.app.audio.play("place")
            if self.model.winner is not None:
                self.app.finish_match(self.model.winner, "Vitória no tabuleiro")
            elif self.model.draw:
                self.app.audio.play("draw")
                self.app.change_scene("armas")

    def draw(self, surface):
        super().draw(surface)
        player = self.model.turn
        text(surface, f"VEZ DO JOGADOR {player + 1}", 32, (550, 138), PLAYER_COLORS[player], True, True)
        for index, rect in enumerate(self.cells):
            panel(surface, rect)
            owner = self.model.cells[index]
            if owner is None:
                text(surface, index + 1, 20, rect.center, MUTED, True)
            else:
                draw_symbol(surface, self.app.state["symbols"][owner], rect.center, 98, PLAYER_COLORS[owner])
        for owner, x in ((0, 110), (1, 910)):
            draw_symbol(surface, self.app.state["symbols"][owner], (x + 35, 330), 84, PLAYER_COLORS[owner])
            text(surface, f"J{owner + 1}", 28, (x + 35, 410), PLAYER_COLORS[owner], True)
            text(surface, f"{self.app.state['scores'][owner]} pontos", 18, (x + 35, 454), MUTED, True)
        text(surface, "1–9 ou clique / empate abre a seleção de armas", 18, (550, 688), MUTED, True)




# 06. ARENA: movimento, disparos, colisões e pausa
def segment_rect(start, delta, rect):
    """Instante de entrada [0, 1] de um segmento em um retângulo."""
    low, high = 0.0, 1.0
    for origin, step, minimum, maximum in (
        (start.x, delta.x, rect.left, rect.right),
        (start.y, delta.y, rect.top, rect.bottom),
    ):
        if abs(step) < 1e-9:
            if origin < minimum or origin > maximum:
                return None
        else:
            first, last = sorted(((minimum-origin)/step, (maximum-origin)/step))
            low, high = max(low, first), min(high, last)
            if low > high:
                return None
    return low


def segment_circle(start, delta, center, radius):
    offset = start - center
    a, c = delta.length_squared(), offset.length_squared() - radius*radius
    if c <= 0:
        return 0.0
    b = 2 * offset.dot(delta)
    discriminant = b*b - 4*a*c
    if a <= 1e-12 or discriminant < 0:
        return None
    impact = (-b - math.sqrt(discriminant)) / (2*a)
    return impact if 0 <= impact <= 1 else None


class BattleWorld:
    """Simulação do duelo sem dependência de tela ou dispositivo de áudio.

    Posições são Vector2 em pixels. dt, invulnerable, cooldown e ttl usam
    segundos; apenas a configuração WEAPONS.cooldown usa milissegundos.
    update devolve nomes de efeitos; o coordenador decide como reproduzi-los.
    winner é None durante o duelo, ou o índice 0/1 de quem venceu.
    """
    def __init__(self, weapons=(0, 0), lives=3):
        self.weapons = tuple(weapons)
        self.bounds = pygame.Rect(50, 170, 1000, 490)
        self.walls = [pygame.Rect(365, 245, 38, 210), pygame.Rect(697, 375, 38, 210)]
        self.reset(lives)

    def reset(self, lives=3):
        """Preserva armas e paredes; recria jogadores, balas e relógios."""
        self.players = [dict(pos=pygame.Vector2(x, 415), hp=lives,
                             invulnerable=0.7, cooldown=0.0) for x in (150, 950)]
        self.bullets, self.winner = [], None
        self.time, self.notice = 0.0, 0.0

    def move_player(self, index, direction, dt):
        """Normaliza a direção e resolve os eixos com subpassos de até 8 px."""
        player = self.players[index]
        direction = pygame.Vector2(direction)
        if direction.length_squared() > 0:
            direction = direction.normalize()
        movement = direction * 255 * dt
        steps = max(1, math.ceil(movement.length() / 8))
        for _ in range(steps):
            for axis in (0, 1):
                amount = movement[axis] / steps
                player['pos'][axis] += amount
                body = pygame.Rect(0, 0, 40, 40)
                body.center = round(player['pos'].x), round(player['pos'].y)
                body.clamp_ip(self.bounds)
                for wall in self.walls:
                    if body.colliderect(wall):
                        if axis == 0:
                            if amount > 0:
                                body.right = wall.left
                            elif amount < 0:
                                body.left = wall.right
                        elif amount > 0:
                            body.bottom = wall.top
                        elif amount < 0:
                            body.top = wall.bottom
                if axis == 0:
                    player['pos'].x = min(self.bounds.right-20, max(self.bounds.left+20, player['pos'].x))
                    if body.centerx != round(player['pos'].x):
                        player['pos'].x = body.centerx
                else:
                    player['pos'].y = min(self.bounds.bottom-20, max(self.bounds.top+20, player['pos'].y))
                    if body.centery != round(player['pos'].y):
                        player['pos'].y = body.centery

    def shoot(self, index):
        """Retorna se houve disparo; a mira é fixada ao criar os projéteis."""
        player, weapon = self.players[index], WEAPONS[self.weapons[index]]
        if player['cooldown'] > 0 or player['hp'] <= 0:
            return False
        aim = self.players[1-index]['pos'] - player['pos']
        aim = aim.normalize() if aim.length_squared() else pygame.Vector2(1, 0)
        for pellet in range(weapon['count']):
            angle = 0 if weapon['count'] == 1 else weapon['spread']*(pellet/(weapon['count']-1)-0.5)
            direction = aim.rotate(angle)
            self.bullets.append(dict(pos=player['pos'].copy(), vel=direction*weapon['speed'],
                                     owner=index, damage=weapon['damage'], radius=weapon['radius'],
                                     ttl=weapon['ttl']))
        player['cooldown'] = weapon['cooldown'] / 1000
        return True

    def update_bullets(self, dt):
        """Testa o percurso completo antes de remover tiros expirados.

        Cada alvo recebe no máximo um acerto durante a invulnerabilidade.
        A vitória é decidida após todos os tiros, permitindo morte simultânea.
        """
        events, survivors = [], []
        for bullet in self.bullets:
            delta = bullet['vel'] * min(dt, bullet['ttl'])
            radius = bullet['radius']
            walls = [segment_rect(bullet['pos'], delta, wall.inflate(2*radius, 2*radius))
                     for wall in self.walls]
            wall_hit = min((value for value in walls if value is not None), default=2.0)
            target = self.players[1-bullet['owner']]
            hit = segment_circle(bullet['pos'], delta, target['pos'], 20+radius)
            if hit is not None and hit < wall_hit:
                if target['invulnerable'] <= 0:
                    target['hp'] = max(0, target['hp']-bullet['damage'])
                    target['invulnerable'] = 0.7
                    events.append('hit')
                continue
            bullet['pos'] += delta
            bullet['ttl'] -= dt
            if wall_hit <= 1 or bullet['ttl'] <= 0:
                continue
            if self.bounds.inflate(2*radius, 2*radius).collidepoint(bullet['pos']):
                survivors.append(bullet)
        self.bullets = survivors
        dead = [player['hp'] <= 0 for player in self.players]
        if all(dead):
            self.reset(1)
            self.notice = 2.5
            events.append('draw')
        elif any(dead):
            self.winner = 1 if dead[0] else 0
        return events

    def update(self, dt, keys):
        """keys é um conjunto de constantes pygame.K_* mantidas pressionadas.

        Move ambos antes dos disparos para que a mira use o mesmo instante.
        """
        if self.winner is not None:
            return []
        self.time += dt
        self.notice = max(0, self.notice-dt)
        controls = [(pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_f),
                    (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN)]
        events = []
        for index, (left, right, up, down, fire) in enumerate(controls):
            player = self.players[index]
            player['invulnerable'] = max(0, player['invulnerable']-dt)
            player['cooldown'] = max(0, player['cooldown']-dt)
            self.move_player(index, ((right in keys)-(left in keys), (down in keys)-(up in keys)), dt)
        for index, (_, _, _, _, fire) in enumerate(controls):
            if fire in keys and self.shoot(index):
                events.append('shoot')
        return events + self.update_bullets(dt)


class ArenaScene(Scene):
    title = 'ARENA'

    def __init__(self, app):
        super().__init__(app)
        self.world = BattleWorld(app.state['weapons'])
        app.state['paused'] = False

    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST or (
            event.type == pygame.ACTIVEEVENT and not event.gain and event.state & 3
        ):
            self.app.state['paused'] = True
            self.app.keys.clear()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.state['paused'] = not self.app.state['paused']
                self.app.keys.clear()
            elif event.key == pygame.K_h and self.app.state['paused']:
                self.app.change_scene('inicio')

    def update(self, dt):
        if self.app.state['paused']:
            return
        for sound in self.world.update(dt, self.app.keys):
            self.app.audio.play(sound)
        if self.world.winner is not None:
            self.app.finish_match(self.world.winner, 'Vitória no duelo')

    def draw(self, surface):
        super().draw(surface)
        for index, player in enumerate(self.world.players):
            color = PLAYER_COLORS[index]
            x = 80 if index == 0 else 650
            text(surface, f'J{index+1}  |  {WEAPONS[self.world.weapons[index]]["name"]}', 21, (x, 118), color)
            text(surface, 'VIDAS  ' + str(player['hp']), 19, (x+235, 120), color)
        panel(surface, self.world.bounds, (29, 35, 40), MUTED)
        for wall in self.world.walls:
            panel(surface, wall, (69, 81, 85), CREAM)
        for bullet in self.world.bullets:
            pygame.draw.circle(surface, PLAYER_COLORS[bullet['owner']], bullet['pos'], bullet['radius'])
        for index, player in enumerate(self.world.players):
            color, pos = PLAYER_COLORS[index], player['pos']
            if player['invulnerable'] > 0:
                pygame.draw.circle(surface, CREAM, pos, 27, 2)
            pygame.draw.circle(surface, color, pos, 22)
            draw_symbol(surface, self.app.state['symbols'][index], pos, 32, BG)
        text(surface, 'J1: WASD + F     |     J2: SETAS + ENTER     |     ESC: PAUSA', 17, (550, 683), MUTED, True)
        if self.world.notice > 0:
            panel(surface, pygame.Rect(280, 183, 540, 42), CREAM)
            text(surface, 'MORTE SIMULTÂNEA!  1 VIDA PARA CADA.', 20, (550, 204), BG, True)
        if self.app.state['paused']:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 180))
            surface.blit(shade, (0, 0))
            panel(surface, pygame.Rect(290, 300, 520, 155), PANEL, CREAM)
            text(surface, 'PAUSA', 44, (550, 345), CREAM, True, True)
            text(surface, 'ESC: retomar  |  H: voltar ao início', 21, (550, 407), TEXT, True)


# 07. TRANSIÇÃO: SELEÇÃO DE ARMAS (APENAS APÓS EMPATE) --------------------------
class WeaponScene(Scene):
    title = "03 / EMPATE NO TABULEIRO — ESCOLHAM AS ARMAS"

    def __init__(self, app):
        super().__init__(app)
        self.active, self.ready = 0, [False, False]
        self.cards = [pygame.Rect(50 + i * 202, 253, 192, 310) for i in range(5)]

    def handle_event(self, event):
        for player in range(2):
            if clicked(event, (100 + player * 460, 157, 430, 60)):
                self.active = player
        for index, rect in enumerate(self.cards):
            if clicked(event, rect):
                self.app.state["weapons"][self.active] = index
                self.ready[self.active] = False
                self.app.audio.play("select")
        if clicked(event, (730, 625, 320, 56)) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
            self.ready[self.active] = True
            self.app.audio.play("select")
            if all(self.ready):
                self.app.change_scene("arena")
            else:
                self.active = 1 - self.active
        elif clicked(event, (50, 625, 230, 56)):
            self.app.change_scene("tabuleiro")

    def draw(self, surface):
        super().draw(surface)
        text(surface, "DEU VELHA. AGORA É NA ARENA.", 32, (550, 117), CREAM, True, True)
        for player in range(2):
            status = "PRONTO" if self.ready[player] else "escolhendo"
            button(surface, f"J{player + 1} / {status}", (100 + player * 460, 157, 430, 60), self.active == player)
        for index, rect in enumerate(self.cards):
            selected = index == self.app.state["weapons"][self.active]
            panel(surface, rect, border=PLAYER_COLORS[self.active] if selected else None)
            draw_icon(surface, "arma", index, (rect.centerx, 321), 96)
            weapon = WEAPONS[index]
            text(surface, weapon["name"], 23, (rect.centerx, 395), CREAM, True)
            details = (f"Dano: {weapon['damage']}", f"Tiros: {weapon['count']}",
                       f"Intervalo: {weapon['cooldown']} ms", f"Alcance: {int(weapon['speed'] * weapon['ttl'])} px")
            for row, label in enumerate(details):
                text(surface, label, 15, (rect.x + 15, 437 + row * 27), MUTED)
        text(surface, "Cada jogador confirma sua escolha. As armas podem se repetir.", 17, (550, 593), MUTED, True)
        button(surface, "Voltar ao tabuleiro", (50, 625, 230, 56))
        button(surface, f"Confirmar J{self.active + 1} / Enter", (730, 625, 320, 56), True)


# 08. RESULTADO E REVANCHE ----------------------------------------------------
class ResultScene(Scene):
    title = "RESULTADO / PLACAR DA SESSÃO"

    def handle_event(self, event):
        enter = event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
        if enter or clicked(event, (105, 594, 280, 60)):
            self.app.change_scene("tabuleiro")
        elif clicked(event, (410, 594, 280, 60)):
            self.app.change_scene("simbolos")
        elif clicked(event, (715, 594, 280, 60)):
            self.app.change_scene("inicio")

    def draw(self, surface):
        super().draw(surface)
        winner, reason = self.app.state["result"]
        color = PLAYER_COLORS[winner]
        draw_symbol(surface, self.app.state["symbols"][winner], (550, 233), 132, color)
        text(surface, f"JOGADOR {winner + 1} VENCEU", 48, (550, 368), color, True, True)
        text(surface, reason, 24, (550, 429), MUTED, True)
        scores = self.app.state["scores"]
        text(surface, f"J1  {scores[0]}     :     {scores[1]}  J2", 36, (550, 506), CREAM, True, True)
        for label, x in (("Revanche / Enter", 105), ("Trocar símbolos", 410), ("Início", 715)):
            button(surface, label, (x, 594, 280, 60), x == 105)
        text(surface, f"Próxima partida: J{self.app.state['starter'] + 1} começa.", 17, (550, 681), MUTED, True)


# 09. ÁUDIO: CANAL RESERVADO, MÚSICA CONTÍNUA E MODO SILENCIOSO ------------------
class AudioManager:
    """Canal 0 exclusivo para a trilha; os demais ficam livres para efeitos."""
    def __init__(self):
        self.enabled, self.muted, self.current = False, False, None
        self.sounds, self.channel = {}, None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.channel, self.enabled = pygame.mixer.Channel(0), True
        except pygame.error:
            return
        for name in ("calm", "battle", "select", "place", "shoot", "hit", "win", "draw"):
            try:
                self.sounds[name] = pygame.mixer.Sound(str(ASSETS / "audio" / f"{name}.wav"))
                self.sounds[name].set_volume(0.45)
            except (OSError, pygame.error):
                continue

    def set_music(self, name):
        """Troca a trilha somente quando muda calm/battle; respeita mudo."""
        if not self.enabled or name == self.current:
            return
        self.current = name
        self.channel.stop()
        if name in self.sounds:
            self.channel.play(self.sounds[name], loops=-1)
        self.channel.set_volume(0 if self.muted else 0.38)

    def play(self, name):
        """Sem dispositivo, arquivo ou canal livre, o jogo segue normalmente."""
        if self.enabled and not self.muted and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        """Silencia a trilha sem reiniciá-la e encerra efeitos ainda ativos."""
        self.muted = not self.muted
        if self.enabled:
            self.channel.set_volume(0 if self.muted else 0.38)
            if self.muted:
                for index in range(1, pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(index).stop()


# 10. COORDENADOR APP: ESTADO DA SESSÃO E CONTRATOS PÚBLICOS --------------------
class App:
    """Uma sessão, um dicionário compartilhado e uma cena ativa por vez.

    state contém symbols, weapons, scores, starter, paused, finished e result.
    As escolhas são índices; scores usa [pontos_J1, pontos_J2].
    starter é quem começa o próximo tabuleiro e alterna ao concluir partidas.
    finished protege o placar até uma nova entrada em tabuleiro.
    """
    def __init__(self, initial_scene="inicio"):
        global RESOURCES
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Velha Arena — Fight : Club")
        RESOURCES = load_assets()
        self.audio = AudioManager()
        self.running, self.keys = True, set()
        self.state = dict(symbols=[0, 1], weapons=[0, 0], scores=[0, 0], starter=0,
                          paused=False, finished=False, result=(0, "Prévia da tela de resultado"))
        self.scene, self.scene_name = None, None
        self.change_scene(initial_scene)

    def change_scene(self, name):
        """Aceita os nomes em SCENES e limpa teclas ao entrar em outra tela.

        Entrar no tabuleiro inicia uma partida com símbolos/placar preservados.
        """
        factories = {"inicio": MenuScene, "ajuda": MenuScene, "simbolos": SymbolScene,
                     "tabuleiro": BoardScene, "armas": WeaponScene, "arena": ArenaScene, "resultado": ResultScene}
        if name not in factories:
            raise ValueError(f"Tela desconhecida: {name}")
        self.keys.clear()
        self.state["paused"] = False
        if name == "tabuleiro":
            self.state["finished"] = False
        self.scene_name = name
        self.scene = factories[name](self)
        self.audio.set_music("battle" if name in ("armas", "arena") else "calm")

    def finish_match(self, winner, reason):
        """Registra um vencedor 0/1 e abre resultado. Retorna se pontuou.

        Chamadas repetidas antes da próxima partida retornam False.
        """
        if self.state["finished"]:
            return False
        if winner not in (0, 1):
            raise ValueError("O vencedor deve ser 0 (J1) ou 1 (J2).")
        self.state["finished"] = True
        self.state["scores"][winner] += 1
        self.state["starter"] = 1 - self.state["starter"]
        self.state["result"] = (winner, reason)
        self.change_scene("resultado")
        self.audio.play("win")
        return True

    def handle_event(self, event):
        """Fecha e alterna áudio em qualquer tela antes de delegar eventos."""
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST or (
            event.type == pygame.ACTIVEEVENT and not event.gain and event.state & 3
        ):
            self.keys.clear()
        if event.type == pygame.KEYUP:
            self.keys.discard(event.key)
        elif event.type == pygame.KEYDOWN:
            if event.key in self.keys:
                return
            self.keys.add(event.key)
            if event.key == pygame.K_m:
                self.audio.toggle()
                return
        self.scene.handle_event(event)

    def update(self, dt):
        """Limita saltos após travamentos; pausas não avançam a simulação."""
        self.scene.update(max(0.0, min(dt, 0.05)))

    def draw(self, surface):
        self.scene.draw(surface)


# 11. MAIN: ÚNICO LAÇO, TESTE RÁPIDO E FINALIZAÇÃO ----------------------------
def executar(initial_scene="inicio", max_frames=0):
    """max_frames=0 executa até fechar; valores positivos limitam o teste.

    O Clock regula 60 FPS sem pausas artificiais entre telas. A finalização
    também ocorre se houver exceção, liberando janela e dispositivo de áudio.
    """
    try:
        app, clock, frames = App(initial_scene), pygame.time.Clock(), 0
        while app.running and (max_frames <= 0 or frames < max_frames):
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                app.handle_event(event)
                if not app.running:
                    break
            if not app.running:
                break
            app.update(dt)
            app.draw(app.screen)
            pygame.display.flip()
            frames += 1
    finally:
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Velha Arena — Fight : Club")
    parser.add_argument("--scene", "--tela", choices=SCENES, default="inicio")
    parser.add_argument("--frames", "--quadros", type=int, default=0)
    args = parser.parse_args()
    if args.frames < 0:
        parser.error("--frames deve ser zero ou positivo")
    executar(args.scene, args.frames)


if __name__ == "__main__":
    main()

