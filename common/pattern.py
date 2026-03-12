import numpy as np

def generate_finder_pattern() -> np.ndarray:
    pattern = np.array([
        [0,0,0,0,0,0,0],
        [0,1,1,1,1,1,0],
        [0,1,0,0,0,1,0],
        [0,1,0,0,0,1,0],
        [0,1,0,0,0,1,0],
        [0,1,1,1,1,1,0],
        [0,0,0,0,0,0,0],
    ])
    #nd:n-dimensional
    return pattern 

def generate_align_pattern() -> np.ndarray:
    pattern = np.array([
        [0,0,0,0,0],
        [0,1,1,1,0],
        [0,1,0,1,0],
        [0,1,1,1,0],
        [0,0,0,0,0]
    ])
    return pattern

