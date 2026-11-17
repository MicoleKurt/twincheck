"""Tiny stopword-based language guesser. No models, no network."""
import re

STOPWORDS = {
    "en": "the and of to in is for with that this you your are on it as be from our we not can will all more have has by or at an".split(),
    "de": "der die das und ist nicht mit für auf den dem des ein eine einer von zu im sie wir ihr ihre auch bei oder wird sind aus nach wie mehr nur über durch".split(),
    "fr": "le la les des et est pas avec pour sur une un du dans vous nous votre vos au aux ce cette qui que plus par ou sont être sans très en".split(),
    "it": "il lo la gli le e è non con per su una un di del della dei in che più da sono questo questa vostro nostro anche o come senza molto al".split(),
    "es": "el la los las y es no con para en una un de del que más por su sus este esta nuestro también o como sin muy al se lo".split(),
    "sv": "och att det som en ett är för med på av den inte till har du vi din ditt dina vår eller från kan mer bara utan om så när".split(),
    "nl": "de het een en is niet met voor op van te in dat je wij uw ook bij of wordt zijn uit naar meer alleen zonder over door".split(),
    "fi": "ja on ei että se tämä kanssa myös tai kun sen ovat voit sinun meidän ilman vain kuin joka mutta niin jos olla saat".split(),
}
_SETS = {k: set(v) for k, v in STOPWORDS.items()}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def words(text):
    return [w.lower() for w in _WORD.findall(text)]


def scores(text):
    ws = words(text)
    return {lang: sum(1 for w in ws if w in s) for lang, s in _SETS.items()}


def guess(text, min_hits=2):
    """Return the language code, or None when the text is too short or too close to call."""
    sc = scores(text)
    ranked = sorted(sc.values(), reverse=True)
    best = max(sc, key=sc.get)
    if sc[best] < min_hits or ranked[0] == ranked[1]:
        return None
    return best
