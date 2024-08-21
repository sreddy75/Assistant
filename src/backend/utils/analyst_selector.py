import pandas as pd


def determine_analyst(filename: str, df: pd.DataFrame) -> str:
    columns = df.columns.str.lower()
    if any(keyword in columns for keyword in ['revenue', 'financial', 'profit', 'cost']):
        return 'financial'
    else:
        return 'data'