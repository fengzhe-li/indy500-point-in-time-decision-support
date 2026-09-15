from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

rows = [
    # -------------------------
    # 2020 - RACER / secondary
    # -------------------------
    [2020, 28, "Ryan Hunter-Reay", 231.263, "BEST_FOUR_LAP_QUAL_SIM",
     "RACER", "PUBLIC_SECONDARY",
     "https://racer.com/2020/08/14/andretti-honda-teams-set-early-fast-friday-pace-at-232mph",
     "Reported as best four-lap qualifying simulation average."],

    [2020, 8, "Marcus Ericsson", 231.233, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 15, "Graham Rahal", 231.057, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 9, "Scott Dixon", 230.840, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 29, "James Hinchcliffe", 230.823, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 12, "Will Power", 230.201, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 30, "Takuma Sato", 230.057, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 98, "Marco Andretti", 230.057, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 88, "Colton Herta", 230.014, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    [2020, 21, "Rinus VeeKay", 229.935, "FOUR_LAP_QUAL_SIM",
     "The Apex / cited session summary", "PUBLIC_SECONDARY",
     "https://www.theapex.racing/2020/08/race-report-2020-indianapolis-500/",
     "Fast Friday four-lap qualifying simulation average."],

    # -------------------------
    # 2021
    # -------------------------
    [2021, 8, "Marcus Ericsson", 231.950, "BEST_FOUR_LAP_QUAL_SIM",
     "2021 Indy 500 public session summary", "PUBLIC_SECONDARY",
     "",
     "Reported fastest four-lap qualifying simulation average on Fast Friday."],

    # -------------------------
    # 2022 - official IndyCar
    # -------------------------
    [2022, 1, "Tony Kanaan", 230.517, "BEST_FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/news/2022/05/05-20-practice",
     "Fastest qualifying-simulation four-lap average."],

    [2022, 18, "David Malukas", 230.287, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/news/2022/05/05-20-practice",
     "Second on qualifying-simulation chart."],

    [2022, 5, "Pato O'Ward", 230.111, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/news/2022/05/05-20-practice",
     "Fourth on qualifying-simulation list."],

    [2022, 48, "Jimmie Johnson", 229.094, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/news/2022/05/05-20-practice",
     "Qualifying simulation after earlier wall contact."],

    [2022, 51, "Takuma Sato", 229.680, "QUAL_SIM_WITH_LIFT",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/news/2022/05/05-20-practice",
     "Forced to lift on third lap; retain as candidate but mark non-clean."],

    # -------------------------
    # 2023 - official IndyCar
    # -------------------------
    [2023, 11, "Takuma Sato", 233.412, "BEST_FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/News/2023/05/05-19-FastFriday",
     "Fastest four-lap qualifying simulation average."],

    [2023, 8, "Marcus Ericsson", 233.112, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/News/2023/05/05-19-FastFriday",
     "Reported four-lap qualifying simulation average."],

    [2023, 2, "Josef Newgarden", 233.085, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/News/2023/05/05-19-FastFriday",
     "Reported four-lap qualifying simulation average."],

    [2023, 12, "Will Power", 233.070, "FOUR_LAP_QUAL_SIM",
     "INDYCAR", "OFFICIAL_EDITORIAL",
     "https://www.indycar.com/News/2023/05/05-19-FastFriday",
     "Reported four-lap qualifying simulation average."],

    # -------------------------
    # 2024
    # -------------------------
    [2024, 2, "Josef Newgarden", 234.063, "BEST_FOUR_LAP_QUAL_SIM",
     "INDYCAR / Motorsport", "OFFICIAL_PLUS_SECONDARY",
     "https://www.indycar.com/News/2024/05/05-17-FastFriday-Report",
     "Fastest four-lap qualifying simulation average."],

    [2024, 3, "Scott McLaughlin", 233.623, "FOUR_LAP_QUAL_SIM",
     "Motorsport", "PUBLIC_SECONDARY",
     "https://www.motorsport.com/indycar/news/indy-500-herta-sets-quickest-lap-at-234974mph-newgarden-tops-four-lap-average/10612225/",
     "Second-fastest four-lap qualifying simulation."],

    [2024, 12, "Will Power", 233.451, "FOUR_LAP_QUAL_SIM",
     "Motorsport", "PUBLIC_SECONDARY",
     "https://www.motorsport.com/indycar/news/indy-500-herta-sets-quickest-lap-at-234974mph-newgarden-tops-four-lap-average/10612225/",
     "Third-fastest four-lap qualifying simulation."],

    [2024, 7, "Alexander Rossi", 233.355, "FOUR_LAP_QUAL_SIM",
     "Motorsport", "PUBLIC_SECONDARY",
     "https://www.motorsport.com/indycar/news/indy-500-herta-sets-quickest-lap-at-234974mph-newgarden-tops-four-lap-average/10612225/",
     "Fourth-fastest four-lap qualifying simulation."],

    [2024, 5, "Pato O'Ward", 233.043, "FOUR_LAP_QUAL_SIM",
     "Motorsport", "PUBLIC_SECONDARY",
     "https://www.motorsport.com/indycar/news/indy-500-herta-sets-quickest-lap-at-234974mph-newgarden-tops-four-lap-average/10612225/",
     "Fifth-fastest four-lap qualifying simulation."],
]

cols = [
    "year",
    "car_number",
    "driver_name",
    "four_lap_average_mph",
    "candidate_type",
    "source_name",
    "source_authority",
    "source_url",
    "notes",
]

df = pd.DataFrame(rows, columns=cols)

df["manual_review_status"] = "PUBLICLY_VERIFIED_CANDIDATE"
df["safe_as_baseline_without_further_audit"] = False

out = OUT / "fast_friday_public_rescue_seed_v1.csv"
df.to_csv(out, index=False)

print(df.groupby("year").size())
print("\nTOTAL PUBLIC RESCUE CANDIDATES:", len(df))
print("\n", df.to_string(index=False))
print("\nOUTPUT:", out.relative_to(ROOT))
