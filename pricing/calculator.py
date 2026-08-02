# pricing/calculator.py

from dataclasses import dataclass


@dataclass
class ModelPricing:
    input_per_million: float
    output_per_million: float


class PricingCalculator:

    PRICING = {

        # ------------------------
        # Groq (currently free)
        # ------------------------

        "groq": {

            "llama-3.3-70b-versatile": ModelPricing(
                input_per_million=0.0,
                output_per_million=0.0
            ),

            "llama-3.1-8b-instant": ModelPricing(
                input_per_million=0.0,
                output_per_million=0.0
            ),
        },

        # ------------------------
        # OpenAI
        # (Update these as pricing changes)
        # ------------------------

        "openai": {

            "gpt-5": ModelPricing(
                input_per_million=1.25,
                output_per_million=10.00
            ),

            "gpt-5-mini": ModelPricing(
                input_per_million=0.25,
                output_per_million=2.00
            ),

            "gpt-4.1-mini": ModelPricing(
                input_per_million=0.40,
                output_per_million=1.60
            ),
        }

    }

    def calculate(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:

        provider = provider.lower()

        if provider not in self.PRICING:
            return 0.0

        if model not in self.PRICING[provider]:
            return 0.0

        pricing = self.PRICING[provider][model]

        input_cost = (
            input_tokens / 1_000_000
        ) * pricing.input_per_million

        output_cost = (
            output_tokens / 1_000_000
        ) * pricing.output_per_million

        return round(input_cost + output_cost, 8)