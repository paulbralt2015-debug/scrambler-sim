#!/usr/bin/env python3
"""
Simulateur pédagogique de brouillage vidéo analogique (temps réel)
  - mode "syster"    : permutation de lignes par trame (type Nagravision Syster)
  - mode "videocrypt": coupure-rotation de chaque ligne (type VideoCrypt)
  - normes couleur   : PAL / SECAM (contraintes chroma prises en compte)

IMPORTANT : simulation logicielle avec PRNG maison. Ce n'est PAS compatible avec
les vrais décodeurs commerciaux (clés, cartes à puce, données VBI propriétaires).

Dépendances : numpy, opencv-python
Exemples :
  python scrambler_sim.py --src 0 --mode syster --std secam --key 1234
  python scrambler_sim.py --src film.mp4 --mode videocrypt --std pal --key 99 --decode
"""
import argparse, time
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

W, H = 720, 576          # image active 625 lignes
FS = 13.5e6              # fréquence d'échantillonnage BT.601
FSC_PAL = 4.43361875e6   # sous-porteuse PAL
FH = 15625.0             # fréquence ligne
CYCLES_PER_LINE_PAL = FSC_PAL / FH   # ~283.7516 -> fraction 0.7516


# --------------------------------------------------------------------------
# Analyse de l'impact sur la chrominance
# --------------------------------------------------------------------------
def pal_phase_error_shift(shift_samples):
    """Erreur de phase (degrés) de la sous-porteuse PAL après décalage horizontal."""
    cyc = shift_samples / FS * FSC_PAL
    e = (cyc % 1.0) * 360.0
    return np.where(e > 180, e - 360, e)


def pal_phase_error_lines(delta_lines):
    """Erreur de phase PAL après déplacement vertical de delta_lines lignes (trame)."""
    cyc = delta_lines * (CYCLES_PER_LINE_PAL % 1.0)
    e = (cyc % 1.0) * 360.0
    return np.where(e > 180, e - 360, e)


# --------------------------------------------------------------------------
# Brouilleur
# --------------------------------------------------------------------------
class Scrambler:
    def __init__(self, mode, std, key, block=32, chroma_safe=True, tol_deg=12.0):
        self.mode, self.std, self.key = mode, std, key
        self.block, self.chroma_safe, self.tol = block, chroma_safe, tol_deg
        # points de coupure autorisés (Videocrypt)
        cuts = np.arange(8, 8 + 256 * 2, 2)           # 256 points candidats
        if std == "pal" and chroma_safe:
            err = np.abs(pal_phase_error_shift(cuts))
            ok = cuts[err <= tol_deg]
            cuts = ok if len(ok) >= 32 else cuts[np.argsort(err)[:64]]
        # SECAM : sous-porteuses en FM, la phase est sans importance
        self.cuts = cuts

    def _rng(self, frame_no, field=0):
        return np.random.default_rng([self.key & 0xFFFFFFFF, frame_no, field])

    # ---- Syster : permutation de lignes dans chaque trame ----------------
    def syster_perm(self, frame_no):
        perm = np.arange(H)
        for f in (0, 1):
            rng = self._rng(frame_no, f)
            lines = np.arange(f, H, 2)                 # lignes de la trame f
            for b in range(0, len(lines), self.block):
                blk = lines[b:b + self.block]
                if self.chroma_safe:
                    # 2 classes (k pair/impair) -> déplacement multiple de 4 lignes
                    # PAL : erreur de phase ~2.3 deg/4 lignes (quasi nulle)
                    # SECAM : alternance Dr/Db conservée (déplacement pair)
                    for cls in (0, 1):
                        sub = blk[cls::2]
                        perm[sub] = sub[rng.permutation(len(sub))]
                else:
                    perm[blk] = blk[rng.permutation(len(blk))]
        return perm

    # ---- Videocrypt : décalage de coupure par ligne -------------------------
    def vc_cuts(self, frame_no):
        rng = self._rng(frame_no)
        return rng.choice(self.cuts, size=H)

    # ---- API ---------------------------------------------------------------
    def encode(self, img, frame_no):
        if self.mode == "syster":
            return img[self.syster_perm(frame_no)]
        cut = self.vc_cuts(frame_no)
        cols = (np.arange(W)[None, :] + cut[:, None]) % W
        return img[np.arange(H)[:, None], cols]

    def decode(self, img, frame_no):
        if self.mode == "syster":
            out = np.empty_like(img)
            out[self.syster_perm(frame_no)] = img
            return out
        cut = self.vc_cuts(frame_no)
        cols = (np.arange(W)[None, :] - cut[:, None]) % W
        return img[np.arange(H)[:, None], cols]

    def chroma_report(self, frame_no):
        """Statistiques d'erreur de chrominance pour la trame courante."""
        if self.std == "secam":
            return "SECAM: FM -> phase non critique ; alternance Dr/Db conservée" \
                   if self.chroma_safe else "SECAM: alternance Dr/Db potentiellement violée"
        if self.mode == "syster":
            perm = self.syster_perm(frame_no)
            d = np.abs(perm - np.arange(H))
            e = np.abs(pal_phase_error_lines(d))
        else:
            e = np.abs(pal_phase_error_shift(self.vc_cuts(frame_no)))
        return f"PAL: erreur phase moy={e.mean():.1f}° max={e.max():.1f}°"


def to_active(frame):
    return cv2.resize(frame, (W, H), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="0")
    ap.add_argument("--mode", choices=["syster", "videocrypt"], default="syster")
    ap.add_argument("--std", choices=["pal", "secam"], default="pal")
    ap.add_argument("--key", type=int, default=1234)
    ap.add_argument("--no-chroma-safe", action="store_true")
    ap.add_argument("--decode", action="store_true", help="afficher aussi le résultat décodé")
    ap.add_argument("--out", help="fichier de sortie (ex: out.mp4)")
    a = ap.parse_args()
    if cv2 is None:
        raise SystemExit("pip install opencv-python numpy")

    src = int(a.src) if a.src.isdigit() else a.src
    cap = cv2.VideoCapture(src)
    scr = Scrambler(a.mode, a.std, a.key, chroma_safe=not a.no_chroma_safe)
    writer = None
    n, t0 = 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        img = to_active(frame)
        enc = scr.encode(img, n)
        view = np.hstack([enc, scr.decode(enc, n)]) if a.decode else enc
        if a.out and writer is None:
            writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), 25,
                                     (view.shape[1], view.shape[0]))
        if writer:
            writer.write(view)
        n += 1
        if n % 25 == 0:
            fps = n / (time.time() - t0)
            print(f"[{n}] {fps:.0f} fps | {scr.chroma_report(n)}")
        cv2.imshow("scrambler_sim", view)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
