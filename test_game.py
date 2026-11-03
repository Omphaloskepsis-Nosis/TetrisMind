from engine import Game

game = Game(seed=42)

print(game.get_state())

game.move_left()
game.rotate_cw()
game.hard_drop()

print("当前分数：", game.score)
print("当前棋盘：")
print(game.board)