import pandas as pd # type: ignore
from rapidfuzz import process, fuzz # type: ignore

class HSNLookup:
    def __init__(self, csv_path: str):
        """Load HSN code dataset (CSV must have columns: hsn_code, Description, rate)."""
        self.df = pd.read_csv(csv_path)
        # normalize columns (case-insensitive)
        self.df.columns = [c.lower() for c in self.df.columns]
        if "hsn" in self.df.columns and "hsn_code" not in self.df.columns:
            self.df.rename(columns={"hsn": "hsn_code"}, inplace=True)
        if "description" not in self.df.columns:
            raise ValueError("CSV must have a Description column")
        if "rate" not in self.df.columns:
            raise ValueError("CSV must have a Rate column")

    def suggest(self, description: str, limit: int = 1):
        """Suggest closest HSN codes for an item description."""
        choices = self.df['description'].tolist()
        matches = process.extract(description, choices, scorer=fuzz.WRatio, limit=limit)
        results = []
        for match, score, idx in matches:
            row = self.df.iloc[idx]
            results.append({
                "hsn_code": row['hsn_code'],
                "Description": row['description'],
                "rate": row['rate'],
                "score": score
            })
        return results

