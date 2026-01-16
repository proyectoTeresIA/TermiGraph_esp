from random import randrange

def create_secretKey():
    number1 = randrange(15)
    number2 = randrange(50)
    number2 = randrange(100)
    random_key = f"{number1}_{number2}_"
    return random_key