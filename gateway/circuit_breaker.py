import time, logging
from enum import Enum

logger = logging.getLogger(__name__)

class State(Enum):
    CLOSED    = "CLOSED"
    OPEN      = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold=3, recovery_timeout=30):
        self.name              = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout  = recovery_timeout
        self.failure_count     = 0
        self.last_failure_time = None
        self.state             = State.CLOSED

    def record_success(self):
        self.failure_count = 0
        self.state = State.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = State.OPEN
            logger.warning(f"[CircuitBreaker:{self.name}] OPENED after {self.failure_count} failures")

    def can_pass(self) -> bool:
        if self.state == State.CLOSED:
            return True
        if self.state == State.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = State.HALF_OPEN
                logger.info(f"[CircuitBreaker:{self.name}] HALF-OPEN — testing recovery")
                return True
            return False
        return True

breakers = {
    "auth":         CircuitBreaker("auth"),
    "user":         CircuitBreaker("user"),
    "order":        CircuitBreaker("order"),
    "notification": CircuitBreaker("notification"),
}