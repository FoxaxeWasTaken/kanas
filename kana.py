#!/usr/bin/env python3
"""Entraînement hiragana/katakana : tape le romaji du caractère affiché.
Mode révision : tous les kana sélectionnés, mélangés.
Mode apprentissage : les kana sont présentés rangée par rangée (あいうえお, かきくけこ...), progression sauvegardée.
Sans option, un menu permet de choisir."""
import argparse
import json
import os
import random
import shutil
import sys
from pathlib import Path

FONT_SIZE = 26  # taille des kana affichés (en pixels, 2 pixels par ligne de terminal) : à ajuster selon ton écran
FONTS = ["/mnt/c/Windows/Fonts/YuGothB.ttc", "/mnt/c/Windows/Fonts/meiryob.ttc", "/mnt/c/Windows/Fonts/msgothic.ttc",
         "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"]
CLEAR = "\033[2J\033[H"
GOAL = 3  # apprentissage : bonnes réponses d'affilée pour qu'un kana compte comme appris
PROGRESS = Path(__file__).with_name("kana_progress.json")  # kana appris : supprime ce fichier pour recommencer à zéro
try:
    from PIL import Image, ImageDraw, ImageFont
    FONT = next((ImageFont.truetype(f, FONT_SIZE) for f in FONTS if os.path.exists(f)), None)
except ImportError:
    FONT = None


def parse(s):
    """Une ligne = une rangée du tableau, renvoyée comme {kana: [romaji acceptés]}."""
    return [{k: r.split("/") for k, r in (t.split("=") for t in line.split())} for line in s.strip().splitlines()]


STANDARD = parse("""
あ=a い=i う=u え=e お=o
か=ka き=ki く=ku け=ke こ=ko
さ=sa し=shi/si す=su せ=se そ=so
た=ta ち=chi/ti つ=tsu/tu て=te と=to
な=na に=ni ぬ=nu ね=ne の=no
は=ha ひ=hi ふ=fu/hu へ=he ほ=ho
ま=ma み=mi む=mu め=me も=mo
や=ya ゆ=yu よ=yo
ら=ra り=ri る=ru れ=re ろ=ro
わ=wa を=wo/o ん=n/nn
""")
VARIANTS = parse("""
が=ga ぎ=gi ぐ=gu げ=ge ご=go
ざ=za じ=ji/zi ず=zu ぜ=ze ぞ=zo
だ=da ぢ=ji/di づ=zu/du で=de ど=do
ば=ba び=bi ぶ=bu べ=be ぼ=bo
ぱ=pa ぴ=pi ぷ=pu ぺ=pe ぽ=po
""")
YOON = {"き": "ky", "し": "sh/sy", "ち": "ch/ty/cy", "に": "ny", "ひ": "hy", "み": "my", "り": "ry",
        "ぎ": "gy", "じ": "j/zy/jy", "ぢ": "j/dy", "び": "by", "ぴ": "py"}
COMBOS = [{k + s: [p + v for p in r.split("/")] for s, v in zip("ゃゅょ", "auo")} for k, r in YOON.items()]
# Katakana seulement (sons étrangers, table officielle 外来語の表記)
KATA_VARIANTS = parse("ヴ=vu")
KATA_COMBOS = parse("""
イェ=ye ウィ=wi ウェ=we ウォ=wo
ヴァ=va ヴィ=vi ヴェ=ve ヴォ=vo ヴュ=vyu
クァ=kwa クィ=kwi クェ=kwe クォ=kwo グァ=gwa
シェ=she/sye ジェ=je/zye/jye チェ=che/tye/cye
ツァ=tsa ツィ=tsi ツェ=tse ツォ=tso
ティ=ti テュ=tyu ディ=di デュ=dyu トゥ=tu ドゥ=du
ファ=fa フィ=fi フェ=fe フォ=fo フュ=fyu
""")
assert [sum(map(len, g)) for g in (STANDARD, VARIANTS, COMBOS, KATA_COMBOS)] == [46, 25, 36, 32]

GROUPS = [  # (option qui désactive, rangées hiragana, ajouts katakana seulement)
    ("no_standard", STANDARD, []),
    ("no_variants", VARIANTS, KATA_VARIANTS),
    ("no_combos", COMBOS, KATA_COMBOS),
]


def kata(s):
    return "".join(chr(ord(c) + 0x60) for c in s)  # hiragana -> katakana : décalage Unicode fixe


def merge(*groups):
    return {k: r for g in groups for row in g for k, r in row.items()}


# Tous les kana, même désactivés, pour retrouver celui qui correspond à une mauvaise réponse
HIRA_ALL = merge(STANDARD, VARIANTS, COMBOS)
KATA_ALL = {**{kata(k): r for k, r in HIRA_ALL.items()}, **merge(KATA_VARIANTS, KATA_COMBOS)}


def big(text):
    """Dessine le texte en grand avec des blocs ▀▄█ (texte normal si Pillow ou police introuvable)."""
    if FONT is None:
        return f"\n      {text}\n"
    _, top, _, bottom = FONT.getbbox("国" + text)  # hauteur fixe : tous les kana gardent la même taille
    left, _, right, _ = FONT.getbbox(text)
    img = Image.new("1", (right - left, bottom - top + 1), 0)
    ImageDraw.Draw(img).text((-left, -top), text, font=FONT, fill=1)
    px, (w, h) = img.load(), img.size
    return "\n".join("    " + "".join(" ▀▄█"[bool(px[x, y]) + 2 * (y + 1 < h and bool(px[x, y + 1]))] for x in range(w))
                     for y in range(0, h, 2))


def build_rows(a):
    """Rangées sélectionnées, dans l'ordre du tableau. Une rangée = liste de (kana, romaji acceptés)."""
    rows = []
    for attr, hira, kata_only in GROUPS:
        if getattr(a, attr):
            continue
        if a.kana != "kata":
            rows += [list(row.items()) for row in hira]
        if a.kana != "hira":
            rows += [[(kata(k), r) for k, r in row.items()] for row in hira] + [list(row.items()) for row in kata_only]
    return rows


def load_progress():
    try:
        return set(json.loads(PROGRESS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def save_progress(saved):
    PROGRESS.write_text(json.dumps(sorted(saved), ensure_ascii=False), encoding="utf-8")


def reset_progress(kanas):
    """Oublie l'apprentissage des kana donnés (les autres sont gardés). Renvoie combien étaient appris."""
    saved, kanas = load_progress(), set(kanas)
    save_progress(saved - kanas)
    return len(saved & kanas)


def menu(a):
    """Modifie les options `a` en place. Renvoie False si l'utilisateur quitte."""
    modes = {"both": "hiragana + katakana", "hira": "hiragana", "kata": "katakana"}
    toggles = [("no_standard", "Standard      (あ, か, さ...)"),
               ("no_variants", "Variantes     (が, ぱ, ヴ...)"),
               ("no_combos", "Combinaisons  (きゃ, しゅ, ファ...)")]
    while True:
        selected = [k for row in build_rows(a) for k, _ in row]
        print(CLEAR + "=== Entraînement kana ===\n")
        print(f"  1. Mode     : < {'apprentissage (rangée par rangée)' if a.learn else 'révision (tout mélangé)'} >")
        print(f"  2. Alphabet : < {modes[a.kana]} >")
        for i, (attr, label) in enumerate(toggles, 3):
            print(f"  {i}. [{' ' if getattr(a, attr) else 'x'}] {label}")
        n_learned = len(load_progress().intersection(selected))
        if a.learn:
            print("  6. Réinitialiser l'apprentissage des kana sélectionnés")
        print(f"\n  {len(selected)} kana sélectionnés" + (f", dont {n_learned} déjà appris" if a.learn else ""))
        c = input("\n  Numéro = changer, Entrée = lancer, q = quitter > ").strip().lower()
        if c == "q":
            return False
        if c == "" and selected:
            return True
        if c == "1":
            a.learn = not a.learn
        elif c == "2":
            keys = list(modes)
            a.kana = keys[(keys.index(a.kana) + 1) % len(keys)]
        elif c in ("3", "4", "5"):
            attr = toggles[int(c) - 3][0]
            setattr(a, attr, not getattr(a, attr))
        elif c == "6" and a.learn and n_learned:
            if input(f"\n  Effacer la progression de {n_learned} kana appris ? (o/N) > ").strip().lower() == "o":
                reset_progress(selected)


def ask(k, answers, last):
    """Affiche le résultat précédent puis le kana en grand. Renvoie (juste ?, ligne de résultat), ou None si 'q'."""
    print(CLEAR + last + "\n\n" + big(k) + "\n")
    rep = input("  romaji (q = quitter) > ").strip().lower()
    if rep == "q":
        return None
    if rep in answers:
        return True, f"  \033[32m✓ {k} = {rep}\033[0m"
    # kana du même alphabet que la question correspondant à la réponse tapée (ex. « ji » -> じ/ぢ)
    typed = "/".join(t for t, r in (KATA_ALL if k in KATA_ALL else HIRA_ALL).items() if rep in r)
    line = f"  \033[31m✗ {k} = {'/'.join(answers)}\033[0m  (tu as tapé « {rep} »"
    return False, line + (f" = {typed})" if typed else ")")


def quiz(pool):
    ok = total = 0
    missed = set()
    last = f"  {len(pool)} kana à réviser."  # résultat de la question précédente, réaffiché après chaque clear
    try:
        while True:
            random.shuffle(pool)
            for k, answers in pool:
                res = ask(k, answers, last)
                if res is None:
                    return
                good, last = res
                total += 1
                ok += good
                if not good:
                    missed.add(k)
                last += f"    score : {ok}/{total}"
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print(f"\nScore : {ok}/{total}" + (f" — à revoir : {' / '.join(sorted(missed))}" if missed else ""))


def learn(rows):
    """Présente une rangée, interroge dessus (avec rappels des rangées déjà sues), puis passe à la suivante
    quand chaque kana de la rangée a été réussi GOAL fois d'affilée."""
    saved = load_progress()
    streak = {k: GOAL for row in rows for k, _ in row if k in saved}  # bonnes réponses d'affilée par kana
    active, todo = [], []  # kana déjà présentés / rangées restant à présenter
    for row in rows:
        if all(k in saved for k, _ in row):
            active += row
        else:
            todo.append(row)

    def known(k):
        return streak.get(k, 0) >= GOAL

    last, prev = "", None
    try:
        while True:
            if all(known(k) for k, _ in active):
                if not todo:
                    print(CLEAR + last + "\n\n  Bravo, tout est appris ! Passe en mode révision pour t'entraîner.")
                    return
                row = todo.pop(0)
                for i, (k, answers) in enumerate(row, 1):
                    card = big(f"{k}  {answers[0]}")  # kana et romaji dessinés ensemble : même taille
                    if max(map(len, card.splitlines())) > shutil.get_terminal_size().columns:
                        card = big(k) + "\n" + big(answers[0])  # terminal trop étroit : romaji sous le kana
                    others = f"\n\n      (accepté aussi : {', '.join(answers[1:])})" if answers[1:] else ""
                    print(CLEAR + last + f"\n\n  Nouveau kana ({i}/{len(row)}) :\n\n" + card + others + "\n")
                    if input("  Entrée = suivant, q = quitter > ").strip().lower() == "q":
                        return
                active += row
                last = "  À toi : tape le romaji des kana que tu viens de voir."
                continue
            cands = [x for x in active if x[0] != prev] or active  # pas deux fois de suite le même kana
            new = [x for x in cands if not known(x[0])]
            old = [x for x in cands if known(x[0])]
            k, answers = random.choice(new if new and (not old or random.random() < 0.7) else old)  # 30 % de rappels
            prev = k
            res = ask(k, answers, last)
            if res is None:
                return
            good, last = res
            streak[k] = streak.get(k, 0) + 1 if good else 0
            last += f"    appris : {sum(s >= GOAL for s in streak.values())}/{sum(map(len, rows))}"
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        saved |= {k for k, s in streak.items() if s >= GOAL}
        save_progress(saved)
        n = sum(k in saved for row in rows for k, _ in row)
        print(f"\nAppris : {n}/{sum(map(len, rows))} (progression sauvegardée)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-l", "--learn", action="store_true", help="mode apprentissage (rangée par rangée)")
    p.add_argument("-k", "--kana", choices=["hira", "kata", "both"], default="both")
    p.add_argument("--no-standard", action="store_true", help="désactive les kana de base (あ, か...)")
    p.add_argument("--no-variants", action="store_true", help="désactive dakuten/handakuten (が, ぱ, ヴ...)")
    p.add_argument("--no-combos", action="store_true", help="désactive les combinaisons (きゃ, ファ...)")
    p.add_argument("--reset", action="store_true",
                   help="efface l'apprentissage des kana sélectionnés (avec -l : puis recommence l'apprentissage)")
    a = p.parse_args()

    if a.reset:
        n = reset_progress(k for row in build_rows(a) for k, _ in row)
        print(f"Apprentissage réinitialisé ({n} kana oubliés).")
        if not a.learn:
            return

    if not sys.argv[1:]:
        try:
            if not menu(a):
                return
        except (KeyboardInterrupt, EOFError):
            return print()
    rows = build_rows(a)
    if not rows:
        p.error("tout est désactivé, rien à réviser")
    if a.learn:
        learn(rows)
    else:
        quiz([x for row in rows for x in row])


if __name__ == "__main__":
    main()
