import string
import random


def get_random_state(length=32):
    state = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                    for _ in range(length))
    return state
