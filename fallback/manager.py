from fallback.circuit_breaker import CircuitBreaker


class CircuitManager:

    def __init__(self):
        self.circuits = {}
        
    def get(self, provider: str):
        if provider not in self.circuits:
            self.circuits[provider] = CircuitBreaker()
        return self.circuits[provider]