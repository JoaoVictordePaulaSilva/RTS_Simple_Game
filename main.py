from game.game import Game


if __name__ == "__main__":
    game = Game()
    try:
        game.run()
    except SystemExit:
        pass
 