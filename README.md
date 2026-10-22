# scrambler-sim

Simulateur pédagogique, en temps réel, de brouillage vidéo analogique :

- **`syster`** : permutation de lignes par trame (principe type Nagravision Syster)
- **`videocrypt`** : coupure-rotation des lignes (principe type VideoCrypt)
- **PAL / SECAM** : prise en compte de l'impact sur la chrominance

> ⚠️ **Simulation uniquement.** Le PRNG et le schéma de clés sont propres à ce projet.
> Le programme n'est **pas compatible** avec les vrais décodeurs commerciaux
> (clés, cartes à puce et données VBI propriétaires) et ne contient aucun outil
> pour décoder de vrais signaux protégés.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Utilisation

```bash
# Webcam, Syster, SECAM
python scrambler_sim.py --src 0 --mode syster --std secam --key 1234

# Fichier vidéo, VideoCrypt, PAL, avec affichage brouillé | décodé
python scrambler_sim.py --src film.mp4 --mode videocrypt --std pal --key 99 --decode

# Export
python scrambler_sim.py --src film.mp4 --mode syster --std pal --out sortie.mp4
```

Touche `Échap` pour quitter. Options : `--no-chroma-safe` pour désactiver les
contraintes de chrominance et observer leur effet.

## Impact sur la couleur

| | PAL | SECAM |
|---|---|---|
| Chroma | QAM, phase de sous-porteuse critique | FM, alternance Dr/Db |
| Syster | Déplacement multiple de 4 lignes ≈ 2,3° d'erreur → permutation dans la même classe | Déplacement pair → alternance Dr/Db conservée |
| VideoCrypt | Points de coupure filtrés selon l'erreur de phase (0,3284 cycle/échantillon à 13,5 MHz) | Phase non critique, ordre des lignes conservé |
| Sans contrainte | Erreur de phase moyenne ≈ 90° | Alternance Dr/Db violée |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Licence

MIT
