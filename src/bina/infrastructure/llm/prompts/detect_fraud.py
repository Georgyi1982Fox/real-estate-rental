from typing import NamedTuple


class FraudDetectionPrompt(NamedTuple):
    """Промпт для детекции мошенничества в объявлении."""
    
    title: str
    description: str
    price: float
    district: str
    rooms: int
    area: float
    
    def __str__(self) -> str:
        return f"""Analyze the following real estate listing for potential fraud indicators.

Listing details:
- Title: {self.title}
- Description: {self.description}
- Price: {self.price} GEL
- District: {self.district}
- Rooms: {self.rooms}
- Area: {self.area} m²

Consider these fraud indicators:
1. Unusually low price compared to market average
2. Vague or suspicious description
3. Missing important details
4. Unrealistic promises
5. Pressure to act quickly
6. Requests for payment outside official channels

Return a JSON object with:
- "is_fraud": boolean (true if fraud is likely)
- "fraud_score": integer (0-100, higher means more suspicious)
- "reasons": array of strings explaining the fraud indicators found

Be conservative in your assessment. Only mark as fraud if there are clear red flags."""