# Entraînement kana

Petit script en ligne de commande pour apprendre et réviser les **hiragana** et **katakana** : un kana s'affiche en grand dans le terminal, tu tapes son romaji.

- **Mode révision** : tous les kana sélectionnés, mélangés, avec score et liste des kana ratés à la fin.
- **Mode apprentissage** : les kana sont présentés rangée par rangée (あいうえお, かきくけこ…). On passe à la rangée suivante quand chaque kana a été réussi 3 fois d'affilée. La progression est sauvegardée dans `kana_progress.json`.

Couvre les kana de base, les variantes (が, ぱ, ヴ…), les combinaisons (きゃ, しゅ…) et les sons étrangers en katakana (ファ, ティ, ヴァ…). En cas d'erreur, le script indique à quel kana correspond ce que tu as tapé.

## Installation

Python 3 suffit. [Pillow](https://pypi.org/project/Pillow/) est optionnel mais recommandé : il permet de dessiner les kana en grand.

```sh
pip install -r requirements.txt
```

Le script cherche une police japonaise (Yu Gothic, Meiryo ou MS Gothic sous Windows/WSL, Droid Sans Fallback sous Linux). Sans Pillow ou sans police trouvée, les kana s'affichent en taille normale. La taille se règle avec `FONT_SIZE` en haut de `kana.py`.

## Utilisation

```sh
python3 kana.py              # menu interactif
python3 kana.py -l           # mode apprentissage
python3 kana.py -k hira      # hiragana seulement (hira, kata ou both)
python3 kana.py --no-combos  # sans les combinaisons
python3 kana.py -l --reset   # efface la progression des kana sélectionnés et recommence
```

`q` pour quitter à tout moment. `python3 kana.py --help` liste toutes les options.
