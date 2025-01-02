import pygame
import pickle
from pygame import Vector2
from pygame.font import Font
import random
import numpy as np
from configurations import *


class ACTIONS:
    LEFT = Vector2(-1, 0)
    RIGHT = Vector2(1, 0)
    UP = Vector2(0, -1)
    DOWN = Vector2(0, 1)

class Object:
    def __init__(self, position=Vector2(0, 0), color=DEFAULT_COLOR, size=Vector2(GRID_SIZE-1, GRID_SIZE-1)):
        self._position = position * GRID_SIZE
        self.color = color
        self.size = size

    @property
    def position(self):
        return self._position / GRID_SIZE

    @position.setter
    def position(self, new_position):
        self._position = new_position * GRID_SIZE

    def render(self, screen):
        pygame.draw.rect(screen, self.color, [self._position.x, self._position.y, self.size.x, self.size.y])

class Food(Object):
    def __init__(self, value=1):
        super().__init__(color=FOOD_COLOR)
        self.value = value
        self.spawn()

    def spawn(self):
        self.position = Vector2(random.randrange(0, GRID_WIDTH), random.randrange(0, GRID_HEIGHT))

class Snake(Object):
    def __init__(self, speed=10, length=3):
        super().__init__(Vector2(GRID_WIDTH-10, GRID_HEIGHT//2))
        self.speed = speed
        self.score = 0
        self.color = (random.randint(0,255),random.randint(0,255),random.randint(0,255))
        self.total_steps = 0
        self.steps = 0
        self.food_eaten = 0
        self.length = length
        rand = random.randint(1,GRID_WIDTH-1)
        self.body = [Object(Vector2(GRID_WIDTH-rand, (GRID_HEIGHT//2)+i+1), self.color) for i in range(length)]
        self.dir = Vector2(0, 1)

    def danger(self, x=None, y=None):
        x = x if x is not None else self.position.x
        y = y if y is not None else self.position.y

        if x < 0 or x >= SCREEN_WIDTH//GRID_SIZE or y < 0 or y >= SCREEN_HEIGHT//GRID_SIZE:
            return True
        for block in self.body[:-1]:  
            if block.position.x == x and block.position.y == y:
                return True
        return False

    def eat(self, food):
        self.length += 1
        self.food_eaten += 1
        self.score += food.value
        self.steps = 0
        food.spawn()

    def render(self, screen):
        for block in self.body:            
            block.render(screen)

    def move(self):
        self.position = (self.position + self.dir)
        self.body.append(Object(self.position, self.color))
        if len(self.body) > self.length:
            self.body.pop(0)
        self.steps += 1
        self.total_steps += 1

class Player(Snake):
    def __init__(self, speed=10, length=3):
        super().__init__(speed, length)

    def decide(self, env):
        prev_dir = self.dir
        for event in pygame.event.get():
            type = event.type
            if type == pygame.QUIT:
                env.game_close = True
            if type == pygame.KEYDOWN:
                key = event.key
                if event.key == pygame.K_ESCAPE:
                    env.game_over = True
                elif prev_dir.x == 0:
                    if key == pygame.K_LEFT or key == pygame.K_a:
                        self.dir = ACTIONS.LEFT
                    elif key == pygame.K_RIGHT or key == pygame.K_d:
                        self.dir = ACTIONS.RIGHT
                elif prev_dir.y == 0:
                    if key == pygame.K_UP or key == pygame.K_w:
                        self.dir = ACTIONS.UP
                    elif key == pygame.K_DOWN or key == pygame.K_s:
                        self.dir = ACTIONS.DOWN

class Agent(Snake):
    q_table = {}
    epsilon = 1.0
    alpha = 0.01
    gamma = 0.95
    min_epsilon = 0.001
    actions = [ACTIONS.LEFT, ACTIONS.RIGHT, ACTIONS.UP, ACTIONS.DOWN]  

    def __init__(self, speed=60, length=3):
        super().__init__(speed, length)

    @staticmethod
    def save(filename="src/Agents/agent_data.pkl"):
        agent_data = {
            "q_table": Agent.q_table,
            "epsilon": Agent.epsilon,
        }
        with open(filename, "wb") as file:
            pickle.dump(agent_data, file)
        print(f"Agent data saved to {filename}.")
    
    @staticmethod
    def load(filename="src/Agents/agent_data.pkl"):
        try:
            with open(filename, "rb") as file:
                agent_data = pickle.load(file)
                Agent.q_table = agent_data["q_table"]
                Agent.epsilon = agent_data["epsilon"]
            print(f"Agent data loaded from {filename}.")
        except FileNotFoundError:
            print(f"No saved agent data found at {filename}. Starting fresh.")

    def decide(self, env):
        state = self.state_representation(env)
        action = self.choose_action(state)
        self.dir = action  
        return action
    def state_representation(self, env):
        food = env.food
        state = []

        food = min([food for food in env.food], key=lambda x: (x.position - self.position).magnitude())
        state.append(1 if food.position.x < self.position.x else 0)
        state.append(1 if food.position.x > self.position.x else 0)
        state.append(1 if food.position.y < self.position.y else 0)
        state.append(1 if food.position.y > self.position.y else 0)

        state.append(1 if self.danger(self.position.x - 1, self.position.y) else 0)
        state.append(1 if self.danger(self.position.x + 1, self.position.y) else 0)
        state.append(1 if self.danger(self.position.x, self.position.y - 1) else 0)
        state.append(1 if self.danger(self.position.x, self.position.y + 1) else 0)

        return tuple(state)


    def choose_action(self, state):
        if state not in Agent.q_table:
            Agent.q_table[state] = np.zeros(len(Agent.actions))

        if np.random.uniform(0, 1) < Agent.epsilon:
            possible_actions = [action for action in Agent.actions if action != -self.dir]
            return random.choice(possible_actions)
        else:
            valid_actions = [action for action in Agent.actions if action != -self.dir]
            q_values = [Agent.q_table[state][Agent.actions.index(action)] for action in valid_actions]
            max_q_index = np.argmax(q_values)
            return valid_actions[max_q_index]
    
    def update_q_table(self, state, action, reward, next_state):
        if state not in Agent.q_table:
            Agent.q_table[state] = np.zeros(len(Agent.actions))
        if next_state not in Agent.q_table:
            Agent.q_table[next_state] = np.zeros(len(Agent.actions))

        action_index = Agent.actions.index(action)
        best_next_action = np.argmax(Agent.q_table[next_state])
        td_target = reward + Agent.gamma * Agent.q_table[next_state][best_next_action]
        td_delta = td_target - Agent.q_table[state][action_index]
        Agent.q_table[state][action_index] += Agent.alpha * td_delta

    def get_reward(self, env):
        if self.danger():
            return -10 
        if self.position == env.food.position:
            return 10
        
        penalty = (env.food.position - self.position).magnitude()*-0.005
        return penalty

    def train(self, env):
        state = self.state_representation(env)
        action = self.decide(env)
        self.dir = action
        self.move()
        reward = self.get_reward(env)
        next_state = self.state_representation(env)
        self.update_q_table(state, action, reward, next_state)
        Agent.epsilon = max(Agent.min_epsilon, Agent.epsilon * 0.9999)

class Game:
    def __init__(self):
        self.snakes = [Agent(), Agent()]
        self.food = [Food(), Food(), Food()]
        self.game_over = False
        self.game_close = False

    def window(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font_style = Font("src/Fonts/Pixelify_Sans/static/PixelifySans-Regular.ttf", 25)

    def UI(self):
        for i, snake in enumerate(self.snakes):
            self.screen.blit(self.font_style.render("Your Score: " + str(snake.score), True, (255, 255, 255)), [i*250, 0])
            self.screen.blit(self.font_style.render("Steps: " + str(snake.steps), True, (255, 255, 255)), [i*250, 25])
        
    def message(self, msg, color):
        mesg = self.font_style.render(msg, True, color)
        self.screen.blit(mesg, [SCREEN_WIDTH / 6, SCREEN_HEIGHT / 3])

    def reset(self):
        self.snake.__init__()
        self.food.spawn()
        self.game_over = False

    def train(self, episodes=350):
        Agent.load()
        total_score = 0
        total_steps = 0
        total_food_eaten = 0
        for episode in range(episodes):
            self.reset()
            while not self.game_over and self.snake.steps < 500+(self.snake.length*5):
                self.snake.train(self)
                if self.snake.danger():
                    self.game_over = True
                if self.snake.position == self.food.position:
                    total_steps += self.snake.steps
                    self.snake.eat(self.food)
            total_score += self.snake.score
            total_food_eaten += self.snake.food_eaten
            average_steps = total_steps / (total_food_eaten) if total_food_eaten > 0 else 1
            average_score = total_score / 50
            if (episode + 1) % 50 == 0:
                print(f"Episode {episode + 1}/{episodes} completed. Average Steps: {average_steps}, Average Score: {average_score}")
                total_score = 0
                total_steps = 0
                total_food_eaten = 0
        Agent.save()
        print("Training complete!")
    
    def multiplayer():
        pass

    def play(self):
        self.window()
        while not self.game_close:
            self.screen.fill(BACKGROUND_COLOR)
            while self.game_over:
                if self.snake.__class__.__name__ == "Agent":
                    self.reset()
                else:
                    self.message("You Lost! Press R-Replay or ESC-Quit", (255, 0, 0))
                    self.UI()
                    pygame.display.update()

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.game_close = True
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                self.game_close = True
                            if event.key == pygame.K_r:
                                self.reset()
            for snake in self.snakes:
                snake.decide(self)
                snake.move()
                
                if snake.danger():
                    game_over = True

                for food in self.food:
                    if snake.position == food.position:
                        snake.eat(food)
                    food.render(self.screen)
                snake.render(self.screen)

            self.UI()

            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        quit()

if __name__ == "__main__":
    game = Game()
    print("Starting training...")
    # game.train(episodes=350)
    Agent.load()
    print("Starting interactive gameplay...")
    game.play()