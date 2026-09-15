from pathlib import Path
import pandas as pd


FILE = Path(
    "weather/evidence/ptsc/"
    "FirestoneTemperatures_current.xlsx"
)


def main():

    print(f"Reading:")
    print(FILE)

    excel = pd.ExcelFile(FILE)

    print()
    print("========================")
    print("SHEETS")
    print("========================")

    for sheet in excel.sheet_names:
        print(sheet)

    print()

    for sheet in excel.sheet_names:

        print()
        print("=================================")
        print(f"SHEET: {sheet}")
        print("=================================")

        df = pd.read_excel(
            FILE,
            sheet_name=sheet,
        )

        print()
        print("Shape:")
        print(df.shape)

        print()
        print("Columns:")
        for col in df.columns:
            print(f" - {col}")

        print()
        print("First 10 rows:")
        print(
            df.head(10).to_string()
        )


if __name__ == "__main__":
    main()