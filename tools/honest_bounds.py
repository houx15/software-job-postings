"""Rambachan & Roth (2023) HonestDiD sensitivity for an event study saved by 13_designA_firmFE.py.
Runs in a SEPARATE venv because the Python port needs torch/cvxpy:  ~/.venvs/honestdid/bin/python tools/honest_bounds.py IN.npz OUT_prefix
Package: honestdid 0.1.1 (Python port, github.com/anzonyquispe/honestdid). Local patch (documented in docs/designA_firmFE_results.md):
  numpy>=2 refuses float() on 1x1 arrays; core.py float(x) -> scalar-safe _sc(x).  RM grid passed explicitly because the
  package default grid (+-20 sd around 0) truncates confidence sets that lie far from 0.
IN.npz: beta (pre..., post...) WITHOUT the reference period, sigma, npre, npost, lvecs (k x npost), lnames.
Writes OUT_prefix_sd.csv and OUT_prefix_rm.csv (git-ignored; under data/).
"""
import sys, warnings
import numpy as np, pandas as pd
import honestdid as hd
warnings.filterwarnings("ignore")

def main(inp, out):
    z = np.load(inp, allow_pickle=True)
    b, S, npre, npost = z["beta"], z["sigma"], int(z["npre"]), int(z["npost"])
    Mvec = [float(x) for x in z["Mvec"]]; Mbar = [float(x) for x in z["Mbarvec"]]
    sd_rows, rm_rows = [], []
    for l, name in zip(z["lvecs"], z["lnames"]):
        l = np.asarray(l, float)
        orig = hd.constructOriginalCS(betahat=b, sigma=S, numPrePeriods=npre, numPostPeriods=npost, l_vec=l, alpha=0.05)
        sd_rows.append(dict(target=name, restriction="original", M=np.nan, lb=float(orig.lb[0]), ub=float(orig.ub[0])))
        r = hd.createSensitivityResults(betahat=b, sigma=S, numPrePeriods=npre, numPostPeriods=npost, l_vec=l,
                                        Mvec=Mvec, alpha=0.05)
        for _, x in r.iterrows():
            sd_rows.append(dict(target=name, restriction="SD", M=float(x.M), lb=float(x.lb), ub=float(x.ub)))
        est = float(l @ b[npre:]); se = float(np.sqrt(l @ S[npre:, npre:] @ l))
        pre = np.concatenate([b[:npre], [0.0]]); G = np.abs(np.diff(pre)).max()
        width = max(Mbar) * G * float(np.abs(l) @ np.arange(1, npost + 1)) + 10 * se
        r = hd.createSensitivityResults_relativeMagnitudes(betahat=b, sigma=S, numPrePeriods=npre, numPostPeriods=npost,
                                                          l_vec=l, Mbarvec=Mbar, alpha=0.05, gridPoints=2000,
                                                          grid_lb=est - width, grid_ub=est + width)
        for _, x in r.iterrows():
            rm_rows.append(dict(target=name, restriction="RM", Mbar=float(x.Mbar), lb=float(x.lb), ub=float(x.ub),
                                grid_lb=est - width, grid_ub=est + width))
    pd.DataFrame(sd_rows).to_csv(out + "_sd.csv", index=False); pd.DataFrame(rm_rows).to_csv(out + "_rm.csv", index=False)
    print(pd.DataFrame(sd_rows).to_string()); print(pd.DataFrame(rm_rows).to_string())

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
