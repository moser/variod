
a_dur = [
  ('a', 880.0),
  ('gis', 830.609),
  ('fis', 739.989),
  ('e', 659.255),
  ('d', 587.330),
  ('cis', 554.365),
  ('h', 493.883),
  ('a', 440.0),
]

a_moll = [
  ('gis', 415.305),
  ('f', 349.228),
  ('e', 329.628),
  ('d', 293.665),
  #('c', 261.626),
  #('h', 246.942),
  #('a', 220.0),
]

step = 6.0 / len(a_dur)
_freqs = [
    ((len(a_dur) - idx - 1) * step, tone[1])
    for idx, tone in enumerate(a_dur + a_moll)
]
print _freqs
