"""Small offline example; uses no downloaded corpus or private model."""
from zaoseq_bopomofo.decoder_v3.lattice import GuardedLattice
from zaoseq_bopomofo.decoder_v3.ngram import NgramBuilder, WittenBellModel
from zaoseq_bopomofo.decoder_v3.script_guard import ScriptGuard
from zaoseq_bopomofo.decoding.scoring import LinearScorer
from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon

texts = ["我在這裡", "這裡很好", "你在哪裡"] * 5
lexicon = Lexicon(
    LexiconEntry(text, (reading,), 1.0, EntrySource.CNS11643)
    for text, reading in [("這", "ㄓㄜˋ"), ("裡", "ㄌㄧˇ"), ("里", "ㄌㄧˇ"), ("理", "ㄌㄧˇ")]
)
tables = NgramBuilder(3).build(texts)
model = WittenBellModel(tables, len(tables.counts[1]))
guard = ScriptGuard(simplified_chars=(), forms={"這里": (1,)})
decoder = GuardedLattice(lexicon, model, LinearScorer(), guard)
for candidate in decoder.generate(("ㄓㄜˋ", "ㄌㄧˇ"), "我在").candidates:
    print(candidate.text)
