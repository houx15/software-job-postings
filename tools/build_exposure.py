"""Download public occupation AI-exposure measures and crosswalk them to the O*NET-SOC 2019 codes used by Revelio.
Sources (all public, see docs/exposure.md):
  Eloundou et al. (Science 2024) occ_level.csv     github.com/openai/GPTs-are-GPTs  (O*NET-SOC 2019 8-digit, O*NET 27.2)
  Felten-Raj-Seamans AIOE (SMJ 2021) + LM-AIOE (2023) github.com/AIOE-Data/AIOE   (SOC 2010 6-digit)
  O*NET-SOC 2010 -> 2019 crosswalk                   onetcenter.org/taxonomy/2019/walk.html
Webb (2020) pct_ai is NOT publicly downloadable (distributed on request, occ1990dd) -> not included; see docs.
Output: data/exposure/exposure_soc6.csv (one row per 2018-SOC 6-digit code, the regression unit)
        data/exposure/exposure_onet8.csv (8-digit, Eloundou only)
"""
import os, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "data", "exposure", "raw"); OUT = os.path.join(HERE, "data", "exposure")
URLS = {
    "occ_level.csv": "https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv",
    "AIOE_DataAppendix.xlsx": "https://raw.githubusercontent.com/AIOE-Data/AIOE/main/AIOE_DataAppendix.xlsx",
    "LM_AIOE.xlsx": "https://raw.githubusercontent.com/AIOE-Data/AIOE/main/Language%20Modeling%20AIOE%20and%20AIIE.xlsx",
    "IG_AIOE.xlsx": "https://raw.githubusercontent.com/AIOE-Data/AIOE/main/Image%20Generation%20AIOE%20and%20AIIE.xlsx",
    "onet_2010_to_2019.csv": "https://www.onetcenter.org/taxonomy/2019/walk/2010_to_2019_Crosswalk.csv?fmt=csv",
}

def fetch():
    os.makedirs(RAW, exist_ok=True)
    for f, u in URLS.items():
        p = os.path.join(RAW, f)
        if not os.path.exists(p):
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (academic research)"})
            open(p, "wb").write(urllib.request.urlopen(req).read())

def main():
    fetch()
    el = pd.read_csv(os.path.join(RAW, "occ_level.csv")).rename(columns={"O*NET-SOC Code": "onet8", "Title": "title"})
    el = el.rename(columns={"dv_rating_beta": "eloundou_beta_gpt4", "human_rating_beta": "eloundou_beta_human",
                            "dv_rating_alpha": "eloundou_alpha_gpt4", "dv_rating_gamma": "eloundou_gamma_gpt4"})
    el["soc6"] = el.onet8.str[:7]
    el.to_csv(os.path.join(OUT, "exposure_onet8.csv"), index=False)
    e6 = el.groupby("soc6")[["eloundou_beta_gpt4", "eloundou_beta_human", "eloundou_alpha_gpt4", "eloundou_gamma_gpt4"]].mean()

    a = pd.read_excel(os.path.join(RAW, "AIOE_DataAppendix.xlsx"), sheet_name="Appendix A").rename(columns={"SOC Code": "soc10", "AIOE": "felten_aioe"})
    lm = pd.read_excel(os.path.join(RAW, "LM_AIOE.xlsx"), sheet_name="LM AIOE").rename(columns={"SOC Code": "soc10", "Language Modeling AIOE": "felten_lm_aioe"})
    ig = pd.read_excel(os.path.join(RAW, "IG_AIOE.xlsx"), sheet_name=0)
    ig = ig.rename(columns={ig.columns[0]: "soc10", ig.columns[-1]: "felten_ig_aioe"})[["soc10", "felten_ig_aioe"]]
    f = a[["soc10", "felten_aioe"]].merge(lm[["soc10", "felten_lm_aioe"]], on="soc10", how="outer").merge(ig, on="soc10", how="left")
    cw = pd.read_csv(os.path.join(RAW, "onet_2010_to_2019.csv"))
    cw["soc10"] = cw["O*NET-SOC 2010 Code"].str[:7]; cw["soc6"] = cw["O*NET-SOC 2019 Code"].str[:7]
    cw = cw[["soc10", "soc6"]].drop_duplicates()
    f6 = f.merge(cw, on="soc10", how="inner").groupby("soc6")[["felten_aioe", "felten_lm_aioe", "felten_ig_aioe"]].mean()
    out = e6.join(f6, how="outer")
    out.to_csv(os.path.join(OUT, "exposure_soc6.csv"))
    print(f"Eloundou: {len(el)} O*NET-8 codes -> {len(e6)} SOC-6; Felten: {len(f)} SOC-2010 -> {len(f6)} SOC-2018-6; merged {len(out)}")
    print(out.corr().round(2))

if __name__ == "__main__":
    main()
