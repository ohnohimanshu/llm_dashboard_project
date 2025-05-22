from datetime import datetime, timedelta
import time

class RateLimiter:
    def __init__(self, limits):
        self.limits = limits
        self.last_request_time = datetime.now() - timedelta(minutes=1)
        self.requests_this_minute = 0
        self.requests_today = 0
        self.day_start = datetime.now().date()
    
    def can_make_request(self):
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if now.date() != self.day_start:
            self.requests_today = 0
            self.day_start = now.date()
        
        # Reset minute counter if a minute has passed
        if (now - self.last_request_time).seconds >= 60:
            self.requests_this_minute = 0
        
        return (self.requests_this_minute < self.limits["requests_per_minute"] and 
                self.requests_today < self.limits["requests_per_day"])
    
    def record_request(self):
        self.requests_this_minute += 1
        self.requests_today += 1
        self.last_request_time = datetime.now()
    
    def get_wait_time(self):
        """Return seconds to wait before next request"""
        if self.requests_this_minute >= self.limits["requests_per_minute"]:
            return 60 - (datetime.now() - self.last_request_time).seconds
        return 0