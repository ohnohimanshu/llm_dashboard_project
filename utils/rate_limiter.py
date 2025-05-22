import time
from functools import wraps

def rate_limit(max_per_minute=10):
    """Rate limiter decorator"""
    min_interval = 60.0 / max_per_minute
    last_time_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            elapsed = current_time - last_time_called[0]
            
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
                
            result = func(*args, **kwargs)
            last_time_called[0] = time.time()
            return result
        return wrapper
    return decorator