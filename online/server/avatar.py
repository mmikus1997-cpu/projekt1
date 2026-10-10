"""0.46: awatar — katalog garderoby i walidacja wyglądu (jedno źródło prawdy po stronie serwera).

Zasady:
- 14 kategorii × 10 rzeczy, w każdej kategorii dokładnie 3 rzeczy VIP (indeksy 7,8,9).
- Wygląd postaci trzymany w state_json['avatar'] = {body:{skin,hair,hairColor}, worn:{kategoria:id}, owned:[id...]}.
- Przy tworzeniu postaci wybór rzeczy zwykłych jest darmowy (trafiają do owned); rzeczy VIP wymagają aktywnego VIP.
- Późniejsze przymiarki (wear) wymagają posiadania rzeczy; kupno (wardrobe) pobiera gotówkę z gry i też pilnuje VIP.
- Katalog jest kosmetyczny: zero wpływu na statystyki, ekonomię i PvP.
"""
CATS=[('glasses','Okulary','👓'),('cap','Czapki','🧢'),('hat','Kapelusze','🎩'),('earrings','Kolczyki','💎'),('necklace','Naszyjniki','📿'),('ring','Pierścionki','💍'),('shirt','Koszulki','👕'),('hoodie','Bluzy','🧥'),('jacket','Kurtki','🥼'),('pants','Spodnie','👖'),('shorts','Spodenki','🩳'),('socks','Skarpetki','🧦'),('shoes','Buty','👟'),('backpack','Plecaki','🎒')]
PREFIX={'glasses':'gl','cap':'cp','hat':'ht','earrings':'er','necklace':'nk','ring':'rg','shirt':'ts','hoodie':'hd','jacket':'jk','pants':'pt','shorts':'sn','socks':'sk','shoes':'bt','backpack':'bp'}
# (nazwa, cena $, vip, kolor główny, kolor dodatkowy) — po 10 na kategorię, ostatnie 3 = VIP
_TABLE={
 'glasses':[('Okrągłe Klasyk',120,0,'#23272b','#8c93a3'),('Kwadratowe Torowe',140,0,'#4a3f2f','#a98c5f'),('Przeciwsłoneczne',160,0,'#1d2126','#39424d'),('Cienkie Metalowe',180,0,'#9aa3ad','#d7dde3'),('Rogowe Grube',200,0,'#5a3d28','#8a6a45'),('Sportowe Opaskowe',240,0,'#22506b','#57a8c9'),('Półksiężyce do Czytania',280,0,'#3c2f45','#b59ad6'),('Złote Awiatory',520,1,'#c9a24b','#f0dfa8'),('Lustrzane Tarcze',560,1,'#6f7d8c','#cfe6f2'),('Serduszka Neon',600,1,'#e0466f','#ff8fb0')],
 'cap':[('Zimowa z Pompkiem',100,0,'#8c3a3a','#e6d6c8'),('Bejsbolówka Klasyk',120,0,'#2b4a6f','#dfe5ea'),('Rowerówka',140,0,'#4f6455','#c2cfae'),('Daszkiem do Tyłu',160,0,'#42484f','#9aa3ad'),('Uszanka',200,0,'#6e4a2f','#e8ddcf'),('Rybacka',220,0,'#3a5a52','#a8c0b5'),('Opaska Sportowa',240,0,'#51336b','#a37fd1'),('Złota Bejsbolówka',480,1,'#b8912f','#f0dfa8'),('Brokatowa',520,1,'#573f7a','#c9b3ec'),('Korona Miejska',640,1,'#a8842e','#ffe9a6')],
 'hat':[('Słomkowy',140,0,'#c9a45f','#7a5a2b'),('Fedora',180,0,'#3a3f46','#8c93a3'),('Cylinder',220,0,'#1d2126','#b8912f'),('Kapelusz Podróżnika',200,0,'#6b5233','#a98c5f'),('Melonik',200,0,'#2b2f34','#d7dde3'),('Panamka',240,0,'#d8cfc0','#8c7f6a'),('Gwiazdora',280,0,'#33306b','#8f8ad1'),('z Piórem',520,1,'#5a2233','#e05a8a'),('Barona',560,1,'#2f2438','#c9a24b'),('Wieniec Laurowy',600,1,'#3f6b3a','#9fd18a')],
 'earrings':[('Małe Kółka',100,0,'#9aa3ad','#d7dde3'),('Sztyfty Złote',140,0,'#c9a24b','#f0dfa8'),('Kółka Stalowe',120,0,'#7d8791','#cfd6dd'),('Koraliki Wiszące',180,0,'#b05f8a','#e8a8c8'),('Czarne Klejnoty',220,0,'#23272b','#6f7d8c'),('Kółka Etniczne',200,0,'#a3703f','#d8b98a'),('Diamentowe Sztyfty',280,0,'#cfd6dd','#ffffff'),('Szafiowe Wiszące',500,1,'#2f4f8f','#8fb0e8'),('Rubinowe',540,1,'#8f2338','#e05a6f'),('Diamentowe Gwiazdy',600,1,'#d7dde3','#ffffff')],
 'necklace':[('Sznurek Skórzany',100,0,'#6e4a2f','#a3703f'),('Łańcuszek Cienki',140,0,'#c9a24b','#f0dfa8'),('Medalion',180,0,'#9aa3ad','#e6d6c8'),('Koraliki Kolorowe',160,0,'#4f8f8a','#e8c86f'),('Choker',200,0,'#23272b','#6f7d8c'),('Łańcuch Gruby',240,0,'#b8912f','#f0dfa8'),('Zawieszka Pełnia',280,0,'#8c93a3','#dfe5ea'),('Złoty Papillon',500,1,'#c9a24b','#ffe9a6'),('Szafirowa Nitka',540,1,'#2f4f8f','#8fb0e8'),('Naszyjnik Władcy',640,1,'#573f7a','#ffd76f')],
 'ring':[('Srebrny',100,0,'#9aa3ad','#d7dde3'),('Złoty Cienki',140,0,'#c9a24b','#f0dfa8'),('Sygnet',200,0,'#b8912f','#8f2338'),('Stalowy',120,0,'#7d8791','#cfd6dd'),('Koralikowy',160,0,'#4f8f8a','#e8a8c8'),('z Turkusem',220,0,'#3f7f8f','#8fd1de'),('Czarny Sygnet',260,0,'#23272b','#b8912f'),('Szafiowy',500,1,'#2f4f8f','#8fb0e8'),('Rubinowy',560,1,'#8f2338','#ff8fa0'),('Pierścień Mistrza',660,1,'#a8842e','#ffe9a6')],
 'shirt':[('Biała Klasyk',100,0,'#e8e6e1','#c2c6cb'),('Koszulka Czarna Basic',100,0,'#23272b','#4a4f56'),('Niebieska Sportowa',140,0,'#2b4a6f','#7fa8cf'),('Czerwona Ulubiona',140,0,'#8f2f3a','#cf7a85'),('Koszulka w Paski',160,0,'#37545c','#c9d6da'),('Miejski Nadruk',180,0,'#42484f','#e0b45f'),('Golf',200,0,'#3f5a46','#8fae95'),('Jedwabna',480,1,'#f0e6d0','#c9a24b'),('Neon',520,1,'#d1e83f','#8fae2f'),('Złoty Print',560,1,'#2b2f34','#f0dfa8')],
 'hoodie':[('Szara z Kapturem',160,0,'#6f7681','#c2c6cb'),('Czarna Basic',160,0,'#23272b','#4a4f56'),('Niebieska Kangurka',200,0,'#2f4f8f','#8fb0e8'),('Zielona Sportowa',200,0,'#3f6b3a','#9fd18a'),('Rozpinana Beżowa',240,0,'#b09a72','#e6d6c8'),('z Nadrukiem',260,0,'#51336b','#c9b3ec'),('Bez Rękawów',240,0,'#8f4a2f','#e0a37f'),('Premium Czarna',520,1,'#1d2126','#c9a24b'),('Neon Glow',560,1,'#3fe0c8','#ff8fb0'),('Bluza Mistrza',620,1,'#a8842e','#ffe9a6')],
 'jacket':[('Wiatrówka',220,0,'#3a6b8f','#a8cde0'),('Jeansowa',260,0,'#3f5a7a','#8fa8c9'),('Bomberka',300,0,'#4a5138','#c2b280'),('Skórzana Czarna',340,0,'#23272b','#6f7d8c'),('Parka',300,0,'#4f6455','#a8bfa0'),('Przeciwdeszczowa',280,0,'#e0b45f','#8f6f2f'),('Pikowana',320,0,'#5a3d4f','#b08aa3'),('Skórzana Premium',600,1,'#3a2418','#c9a24b'),('Kurtka Scena',640,1,'#573f7a','#e8c86f'),('Złoty Bomber',680,1,'#a8842e','#ffe9a6')],
 'pants':[('Jeansy Niebieskie',140,0,'#3f5a7a','#8fa8c9'),('Czarne Garniturowe',160,0,'#23272b','#4a4f56'),('Dresy Szare',140,0,'#6f7681','#c2c6cb'),('Beżowe Chinosy',180,0,'#b09a72','#e6d6c8'),('Ciemne Jeansy',160,0,'#2b3a4f','#7a90ad'),('Kargo',220,0,'#5a614f','#a8ad9a'),('W Kratę',200,0,'#51336b','#a37fd1'),('Skórzane',520,1,'#3a2418','#c9a24b'),('Białe Markowe',560,1,'#e8e6e1','#c9a24b'),('Złote Dresy',620,1,'#a8842e','#ffe9a6')],
 'shorts':[('Sportowe Czarne',100,0,'#23272b','#4a4f56'),('Jeansowe',140,0,'#3f5a7a','#8fa8c9'),('Dresowe Szare',120,0,'#6f7681','#c2c6cb'),('Beżowe',140,0,'#b09a72','#e6d6c8'),('Płócienne',160,0,'#d8cfc0','#8c7f6a'),('Bojówki',200,0,'#5a614f','#a8ad9a'),('Spodenki w Paski',180,0,'#37545c','#c9d6da'),('Neon Premium',480,1,'#d1e83f','#3fe0c8'),('Skórzane Spodenki',520,1,'#3a2418','#c9a24b'),('Mistrzowskie',560,1,'#a8842e','#ffe9a6')],
 'socks':[('Białe Sportowe',60,0,'#e8e6e1','#c2c6cb'),('Czarne Klasyczne',60,0,'#23272b','#4a4f56'),('W Paski',80,0,'#37545c','#c9d6da'),('W Kropki',80,0,'#8f2f3a','#e0b45f'),('Czerwone',80,0,'#8f2f3a','#cf7a85'),('Kolorowy Mix',100,0,'#4f8f8a','#e8c86f'),('Wysokie Sportowe',120,0,'#2b4a6f','#7fa8cf'),('Złote',380,1,'#c9a24b','#ffe9a6'),('Neonowe',420,1,'#d1e83f','#3fe0c8'),('Królewskie',460,1,'#573f7a','#ffd76f')],
 'shoes':[('Trampki Białe',140,0,'#e8e6e1','#c2c6cb'),('Trampki Czarne',140,0,'#23272b','#4a4f56'),('Biegówki',180,0,'#2b4a6f','#7fa8cf'),('Klasyczne Skórzane',220,0,'#4a3226','#a3703f'),('Wysokie Sneakersy',240,0,'#6f2f3a','#e0a3b0'),('Trekowe',260,0,'#5a614f','#a8ad9a'),('Halówki',280,0,'#3a3f46','#9aa3ad'),('Premium Sneakersy',560,1,'#23272b','#f0dfa8'),('Skórzane Złote',620,1,'#a8842e','#ffe9a6'),('Buty Mistrza',680,1,'#573f7a','#ffd76f')],
 'backpack':[('Miejski Mały',160,0,'#4a3226','#a3703f'),('Szkolny',180,0,'#2b4a6f','#7fa8cf'),('Sportowy',200,0,'#3f6b3a','#9fd18a'),('Turystyczny',260,0,'#5a614f','#a8ad9a'),('Czarny Minimal',220,0,'#23272b','#4a4f56'),('Skaterski',240,0,'#8f2f3a','#e0b45f'),('Taktyczny',300,0,'#37545c','#7a90ad'),('Premium Skórzany',560,1,'#3a2418','#c9a24b'),('Neon City',600,1,'#3fe0c8','#ff8fb0'),('Plecak Podróżnika',660,1,'#573f7a','#ffd76f')],
}
def _build():
 items={}
 for k,rows in _TABLE.items():
  pre=PREFIX[k];lst=[]
  for i,(n,p,vip,c,c2) in enumerate(rows):
   lst.append(dict(id=f'{pre}{i+1}',k=k,n=n,p=p,vip=bool(vip),c=c,c2=c2,v=i))
  items[k]=lst
 return items
ITEMS=_build()
ID2ITEM={it['id']:it for lst in ITEMS.values() for it in lst}
SKINS=['#f6d7b8','#eec39a','#d9a066','#b07b4f','#8d5a33','#6b4226']
HAIRS=['Łysina','Krótkie','Boczne','Kręcone','Długie','Jeż']
HAIRCOLORS=['#1b1b1b','#4a2f23','#8a5a2b','#c9873c','#b8b8bd','#2e5f8a','#c94f7c','#3f8f4f']
GENDERS=('m','k')  # 0.48: płeć sylwetki awatara (m=mężczyzna, k=kobieta); starsze postacie → 'm'
BODIES=dict(skins=SKINS,hairs=HAIRS,hairColors=HAIRCOLORS,genders=list(GENDERS))
CATKEYS=[c[0] for c in CATS]

def default():return {'body':{'gender':'m','skin':0,'hair':1,'hairColor':0},'worn':{},'owned':[]}

def brief(state):
 """Kompaktowy wygląd do list: body + warstwy (kosmetyka + przedmioty gry z priorytetem)."""
 body=_body_of(state)
 av=state.get('avatar') if isinstance(state.get('avatar'),dict) else {}
 layers,_=compose(state)
 return {'body':body,'worn':clean_worn(av.get('worn')),'layers':layers}

def _clamp(v,lo,hi):
 try:v=int(v)
 except (TypeError,ValueError):return lo
 return max(lo,min(hi,v))

def clean_worn(worn):
 """Zostawia tylko poprawne pary (kategoria, rzecz). Zwraca czysty worn."""
 if not isinstance(worn,dict):return {}
 return {k:v for k,v in worn.items() if k in ITEMS and isinstance(v,str) and ID2ITEM.get(v,{}).get('k')==k}

SLOT_OF={'cap':'head','hat':'head','pants':'legs','shorts':'legs'}

def validate(av,vip_active,owned,allow_new_owned):
 """Zwraca (clean, err). clean zawiera body/worn/new_owned. allow_new_owned=True tylko przy tworzeniu postaci."""
 d=default()
 if not isinstance(av,dict):return None,'Przygotuj wygląd od nowa.'
 b=av.get('body') or {}
 g=b.get('gender',d['body'].get('gender','m'))
 if g not in GENDERS:return None,'Płeć awatara to „m” albo „k”.'
 body={'gender':g,'skin':_clamp(b.get('skin',d['body']['skin']),0,len(SKINS)-1),'hair':_clamp(b.get('hair',d['body']['hair']),0,len(HAIRS)-1),'hairColor':_clamp(b.get('hairColor',d['body']['hairColor']),0,len(HAIRCOLORS)-1)}
 raw=av.get('worn') or {}
 if not isinstance(raw,dict):return None,'Wygląd jest uszkodzony — przygotuj go od nowa.'
 if len(raw)>len(CATS):return None,'Za dużo rzeczy naraz.'
 worn={};new=[]
 for k,i in raw.items():
  if k not in ITEMS:return None,'Nieznana kategoria garderoby.'
  it=ID2ITEM.get(i) if isinstance(i,str) else None
  if not it or it['id'] not in [x['id'] for x in ITEMS[k]]:return None,'Nie ma takiej rzeczy: '+str(i)+'.'
  if it['vip'] and not vip_active:return None,'Rzeczy VIP są dostępne z aktywnym VIP.'
  if not allow_new_owned and it['id'] not in owned:return None,'Najpierw kup tę rzecz w sklepie: '+it['n']+'.'
  worn[k]=it['id'];new.append(it['id'])
  slot=SLOT_OF.get(k)  # 0.47: czapka i kapelusz (oraz spodnie i spodenki) to jeden slot — nowa rzecz ZAMIENIA Starą, nie nakłada się podwójnie
  if slot:
   for k2 in [x for x in worn if x!=k and SLOT_OF.get(x)==slot]:del worn[k2]
 return {'body':body,'worn':worn,'new_owned':sorted(set(new))},None

"""0.47: wygląd awatara z przedmiotów gry — jedno źródło prawdy (serwer) dla klienta.

GAME_LOOKS mapuje id przedmiotu z economy (ITEMS + DUNGEON_ITEMS) na warstwę awatara:
 layer: gloves | outfit | shoes | band | crown | helmet | backpack | amulet
Priorytet: przedmioty gry nadlatują na kosmetyczną garderobę (hełm zdejmuje czapkę itd.).
"""
GAME_LOOKS={
 'basic-gloves':dict(layer='gloves',c='#c8b28a',c2='#8a6f47'),
 'urban-gloves':dict(layer='gloves',c='#b03a3a',c2='#e0d6c8'),
 'counter-gloves':dict(layer='gloves',c='#2f4f8f',c2='#8fb0e8'),
 'rekawice-lochu':dict(layer='gloves',c='#4a2f5a',c2='#c9a24b'),
 'basic-shirt':dict(layer='outfit',c='#34382e',c2='#e5bf7e'),
 'focus-shirt':dict(layer='outfit',c='#2f5f5a',c2='#8fd1c9'),
 'captain-shirt':dict(layer='outfit',c='#4a3a6b',c2='#f0dfa8'),
 'basic-shoes':dict(layer='shoes',c='#e8e6e1',c2='#c2c6cb'),
 'sprint-shoes':dict(layer='shoes',c='#e07f2f',c2='#f2e2c8'),
 'agile-shoes':dict(layer='shoes',c='#3f8f4f',c2='#c9e8cf'),
 'buty-cienia':dict(layer='shoes',c='#23272b',c2='#4a4f56'),
 'basic-accessory':dict(layer='band',c='#8c93a3',c2='#d7dde3'),
 'tactical-band':dict(layer='band',c='#22506b',c2='#57a8c9'),
 'analyst-band':dict(layer='band',c='#51336b',c2='#c9b3ec'),
 'korona-wladcy':dict(layer='crown',c='#c9a24b',c2='#ffe9a6'),
 'basic-helmet':dict(layer='helmet',c='#d7dde3',c2='#8c93a3'),
 'spartan-helmet':dict(layer='helmet',c='#b08d3f',c2='#e8d6a8'),
 'helm-lochu':dict(layer='helmet',c='#3a2f45',c2='#c9a24b'),
 'basic-backpack':dict(layer='backpack',c='#8a6a45',c2='#c9a45f'),
 'trekker-pack':dict(layer='backpack',c='#3f6b3a',c2='#9fd18a'),
 'basic-amulet':dict(layer='amulet',c='#8a6a45',c2='#b8b8bd'),
 'focus-amulet':dict(layer='amulet',c='#2f4f8f',c2='#8fd1de'),
 'charm-amulet':dict(layer='amulet',c='#8f2338',c2='#ff8fb0'),
}
# hełm chowa kosmetyczne nakrycia głowy; strój gry przykrywa kosmulkę/bluzę/kurtkę
COVERS={'helmet':('cap','hat'),'outfit':('shirt','hoodie','jacket'),'amulet':('necklace',)}
GAME_IDS=set(GAME_LOOKS)

def _body_of(state):
 av=state.get('avatar') if isinstance(state.get('avatar'),dict) else {}
 b=av.get('body') if isinstance(av.get('body'),dict) else {}
 g=b.get('gender')
 return {'gender':g if g in GENDERS else 'm','skin':_clamp(b.get('skin',0),0,len(SKINS)-1),'hair':_clamp(b.get('hair',1),0,len(HAIRS)-1),'hairColor':_clamp(b.get('hairColor',0),0,len(HAIRCOLORS)-1)}

def compose(state):
 """(layers, body): warstwy kosmetyczne + nałożone przedmioty gry (gra ma priorytet)."""
 body=_body_of(state)
 layers={}
 av=state.get('avatar') if isinstance(state.get('avatar'),dict) else {}
 for k,v in (av.get('worn') or {}).items():
  if k in ITEMS:layers[k]=v
 for slot,item_id in (state.get('equipped') or {}).items():
  look=GAME_LOOKS.get(item_id)
  if not look:continue
  layers[look['layer']]=item_id
  for k in COVERS.get(look['layer'],()):
   layers.pop(k,None)
 return layers,body

def gear(state,catalog_names=None):
 """Ruchy bojowe: co zawodnik ma „w rękach” (do animacji PvP)."""
 eq=state.get('equipped') or {}
 out={}
 for slot,key in (('gloves','gloves'),('shoes','shoes'),('helmet','helmet')):
  item_id=eq.get(slot)
  if item_id and item_id in GAME_LOOKS:
   out[key]=item_id
 return out

def layer_meta(item_id,catalog):
 """(k, kolory, nazwa) dla id kosmetycznego albo 'g:'+id przedmiotu gry."""
 if item_id.startswith('g:'):
  look=GAME_LOOKS.get(item_id[2:])
  return (look['layer'],look['c'],look['c2']) if look else None
 it=ID2ITEM.get(item_id)
 return (it['k'],it['c'],it['c2']) if it else None
