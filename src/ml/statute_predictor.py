import json
from pathlib import Path
from typing import List, Dict, Tuple
from src.utils.logger import LegalAdvisorLogger


class StatutePredictor:
    """
    Predicts relevant statutes and IPC sections based on legal topic.
    Uses topic mapping to retrieve applicable statutes.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize statute predictor

        Args:
            data_dir: Directory containing statutes.json
        """
        self.data_dir = Path(data_dir)

        # Load statutes database
        statutes_file = self.data_dir / "statutes.json"
        with open(statutes_file, "r") as f:
            self.statutes_db = json.load(f)

        print(f"Statute predictor initialized with {len(self.statutes_db)} topics")

    def predict(self, topic: str) -> Dict:
        """
        Predict statutes for a given legal topic

        Args:
            topic: Legal topic (e.g., "defamation")

        Returns:
            Dictionary containing relevant statutes and their details
        """
        if topic not in self.statutes_db:
            return {}

        statutes_data = self.statutes_db[topic]

        # Extract statute information
        result = {
            "topic": topic,
            "statutes": [],
            "details": {},
        }

        for statute_code, statute_info in statutes_data.items():
            result["statutes"].append(statute_code)
            result["details"][statute_code] = {
                "section": statute_info.get("section", ""),
                "title": statute_info.get("title", ""),
                "penalties": statute_info.get("penalties", ""),
            }

        # Log prediction
        LegalAdvisorLogger.log_statute_prediction(topic, result["statutes"])

        return result

    def get_statute_details(self, statute_code: str) -> Dict:
        """
        Get detailed information about a specific statute

        Args:
            statute_code: Statute code (e.g., "499" for IPC 499)

        Returns:
            Dictionary with statute details
        """
        # Search through all topics
        for topic, statutes_data in self.statutes_db.items():
            if statute_code in statutes_data:
                return statutes_data[statute_code]

        return {}

    def get_topics(self) -> List[str]:
        """Get list of all available topics"""
        return list(self.statutes_db.keys())


if __name__ == "__main__":
    predictor = StatutePredictor()

    # Test predictions
    test_topics = [
        "defamation",
        "labour_employment",
        "property_law",
        "cyber_law",
        "family_law",
    ]

    for topic in test_topics:
        print(f"\nTopic: {topic}")
        result = predictor.predict(topic)
        for statute in result["statutes"]:
            details = result["details"][statute]
            print(f"  {statute}: {details['title']}")
            print(f"    Penalties: {details['penalties']}")
