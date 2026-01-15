# src/guitar_brain.py
import itertools
import re

# --- CONSTANTES E TEORIA ---
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TUNING_VALUES = [4, 9, 2, 7, 11, 4] # E A D G B E

CHORD_FORMULAS = {
    'Major': [0, 4, 7],
    'm': [0, 3, 7],
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9],
    'add9': [0, 4, 7, 14],
    'madd9': [0, 3, 7, 14],
    '7': [0, 4, 7, 10],
    'm7': [0, 3, 7, 10],
    'maj7': [0, 4, 7, 11],
    '9': [0, 4, 7, 10, 14],
    'm9': [0, 3, 7, 10, 14],
    'maj9': [0, 4, 7, 11, 14],
    'm7b5': [0, 3, 6, 10],
    'dim7': [0, 3, 6, 9],
    '7sus4': [0, 5, 7, 10],
    '7sus2': [0, 2, 7, 10],
}


CAGED_PATTERNS = {
    'Major': [
        [-1, 3, 2, 0, 1, 0],  # C shape
        [-1, 0, 2, 2, 2, 0],  # A shape
        [3, 2, 0, 0, 0, 3],   # G shape
        [0, 2, 2, 1, 0, 0],   # E shape
        [-1, -1, 0, 2, 3, 2], # D shape
    ],
    'm': [
        [-1, 0, 2, 2, 1, 0],  # Am shape
        [0, 2, 2, 0, 0, 0],   # Em shape
        [-1, -1, 0, 2, 3, 1], # Dm shape
    ],
    '7': [
        [-1, 3, 2, 3, 1, 0],  # C7 shape
        [-1, 0, 2, 0, 2, 0],  # A7 shape
        [3, 2, 0, 0, 0, 1],   # G7 shape
        [0, 2, 0, 1, 0, 0],   # E7 shape
        [-1, -1, 0, 2, 1, 2], # D7 shape
    ],
    'm7': [
        [-1, 0, 2, 0, 1, 0],  # Am7 shape
        [0, 2, 2, 0, 3, 0],   # Em7 shape
        [-1, -1, 0, 2, 1, 1], # Dm7 shape
    ],
    'maj7': [
        [-1, 3, 2, 0, 0, 0],  # Cmaj7 shape
        [-1, 0, 2, 1, 2, 0],  # Amaj7 shape
        [3, 2, 0, 0, 0, 2],   # Gmaj7 shape
        [0, 2, 1, 1, 0, 0],   # Emaj7 shape
        [-1, -1, 0, 2, 2, 2], # Dmaj7 shape
    ],
}

CAGED_BONUS = 20
FINGER_PENALTY = 0.5

FLAT_TO_SHARP = {
    'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
}

ENHARMONIC_EQUIV = {
    'Cb': 'B', 'Fb': 'E', 'E#': 'F', 'B#': 'C'
}

def get_note_name(value):
    return NOTES[value % 12]

def normalize_root_name(name):
    if not name:
        return name
    name = name.strip().replace('♭', 'b').replace('♯', '#')
    if not name:
        return name
    letter = name[0].upper()
    accidental = name[1] if len(name) > 1 and name[1] in ('#', 'b') else ''
    root = letter + accidental
    root = ENHARMONIC_EQUIV.get(root, root)
    root = FLAT_TO_SHARP.get(root, root)
    return root

def get_chord_notes(root_name, quality):
    root_name = normalize_root_name(root_name)
    root_val = NOTES.index(root_name)
    intervals = get_chord_intervals(quality)
    return [get_note_name(root_val + i) for i in intervals]

def get_chord_intervals(quality):
    if quality is None:
        return list(CHORD_FORMULAS['Major'])
    if isinstance(quality, (list, tuple, set)):
        return list(quality)

    q = str(quality).strip()
    if not q:
        return list(CHORD_FORMULAS['Major'])
    if q in CHORD_FORMULAS:
        return list(CHORD_FORMULAS[q])

    q = q.replace('♭', 'b').replace('♯', '#')
    ql = q.lower().replace('major', 'maj').replace('minor', 'm').replace('min', 'm')
    if ql.startswith('o'):
        ql = ql.replace('o', 'dim', 1)
    ql = ql.replace('ma7', 'maj7').replace('ma9', 'maj9').replace('ma13', 'maj13')
    ql = ql.replace('o7', 'dim7').replace('°7', 'dim7').replace('°', 'dim')
    ql = ql.replace('7+', '7#5').replace('7-', '7b5')
    ql = ql.replace('5+', '#5').replace('5-', 'b5')
    ql = ql.replace('9+', '#9').replace('9-', 'b9')
    ql = ql.replace('11+', '#11').replace('11-', 'b11')
    ql = ql.replace('13+', '#13').replace('13-', 'b13')

    if 'm7b5' in ql or 'ø' in ql:
        return list(CHORD_FORMULAS['m7b5'])

    base = 'maj'
    if 'sus2' in ql:
        base = 'sus2'
    elif 'sus4' in ql or ('sus' in ql and 'sus2' not in ql):
        base = 'sus4'
    elif 'dim' in ql:
        base = 'dim'
    elif 'aug' in ql or '+' in ql:
        base = 'aug'
    elif ql.startswith('m') and not ql.startswith('maj'):
        base = 'm'

    if base == 'sus2':
        intervals = [0, 2, 7]
    elif base == 'sus4':
        intervals = [0, 5, 7]
    elif base == 'dim':
        intervals = [0, 3, 6]
    elif base == 'aug':
        intervals = [0, 4, 8]
    elif base == 'm':
        intervals = [0, 3, 7]
    else:
        intervals = [0, 4, 7]

    has_maj7 = 'maj7' in ql or 'maj9' in ql or 'maj13' in ql
    has_7 = '7' in ql

    if 'dim7' in ql:
        intervals.append(9)
    elif has_maj7:
        intervals.append(11)
    elif has_7:
        intervals.append(10)

    has_6_9 = ('6/9' in ql) or ('69' in ql)
    if has_6_9:
        intervals.append(9)
        intervals.append(14)
    elif '6' in ql and '16' not in ql and 'maj6' not in ql:
        intervals.append(9)

    is_add9 = ('add9' in ql) or ('add2' in ql)
    if is_add9:
        intervals.append(14)
    elif '9' in ql:
        intervals.append(14)
        if (not has_7 and not has_maj7 and 'm9' not in ql and 'maj9' not in ql
                and not is_add9 and not has_6_9):
            intervals.append(10)

    if '11' in ql:
        intervals.append(17)
    if '13' in ql:
        intervals.append(21)

    # Alteracoes
    for alt, degree in re.findall(r'([b#])(5|9|11|13)', ql):
        if degree == '5':
            if 7 in intervals:
                intervals.remove(7)
            if 8 in intervals:
                intervals.remove(8)
            if 6 in intervals:
                intervals.remove(6)
            intervals.append(6 if alt == 'b' else 8)
        elif degree == '9':
            if 14 in intervals:
                intervals.remove(14)
            intervals.append(13 if alt == 'b' else 15)
        elif degree == '11':
            if 17 in intervals:
                intervals.remove(17)
            intervals.append(16 if alt == 'b' else 18)
        elif degree == '13':
            if 21 in intervals:
                intervals.remove(21)
            intervals.append(20 if alt == 'b' else 22)

    return sorted(set(intervals))

def parse_chord_symbol(symbol):
    if not symbol:
        return None
    s = symbol.strip().replace('♭', 'b').replace('♯', '#')
    s = re.sub(r'[\.,;:]+$', '', s)
    simplified = False
    s_no_paren = re.sub(r'\([^)]*\)', '', s)

    slash_idx = s_no_paren.find('/')
    if slash_idx != -1 and slash_idx + 1 < len(s_no_paren):
        if s_no_paren[slash_idx + 1].upper() in 'ABCDEFG':
            s = s.split('/', 1)[0]
            simplified = True

    m = re.match(r'^([A-Ga-g])([#b]?)(.*)$', s)
    if not m:
        return None
    root = normalize_root_name(m.group(1).upper() + m.group(2))
    rem = m.group(3)

    rem = rem.replace('Δ', 'maj')
    rem = re.sub(r'(?i)maj', 'maj', rem)
    rem = re.sub(r'(?<![a-zA-Z])M(?=\d)', 'maj', rem)

    mods = []
    for group in re.findall(r'\(([^)]*)\)', rem):
        for part in re.split(r'[\s,/]+', group):
            part = part.strip()
            if not part:
                continue
            part = part.replace('+', '#').replace('-', 'b')
            m = re.match(r'^(\d+)([b#])$', part)
            if m:
                part = f"{m.group(2)}{m.group(1)}"
            mods.append(part)

    rem = re.sub(r'\([^)]*\)', '', rem)
    rem = rem.strip()
    rem_l = rem.lower()

    if rem_l in ('', 'maj', 'major'):
        quality = 'Major'
    elif rem_l in ('m', 'min', 'minor'):
        quality = 'm'
    else:
        quality = rem_l

    if mods:
        quality = f"{quality}{''.join(mods)}"

    return root, quality, simplified

# --- RANKING DE COMPLEXIDADE (TIERS) ---

def _matches_caged_pattern(frets, base):
    shifts = set()
    for b, f in zip(base, frets):
        if b == -1:
            if f != -1:
                return False
        elif b == 0:
            if f == -1:
                return False
            shifts.add(0 if f == 0 else f)
        else:
            if f == -1:
                return False
            shifts.add(f - b)
    if not shifts:
        return False
    for shift in shifts:
        if shift < 0:
            continue
        ok = True
        for b, f in zip(base, frets):
            if b == -1:
                if f != -1:
                    ok = False
                    break
            elif b == 0:
                if (shift == 0 and f != 0) or (shift > 0 and f != shift):
                    ok = False
                    break
            else:
                if f != b + shift:
                    ok = False
                    break
        if ok:
            return True
    return False


def _caged_quality_key(quality):
    if quality in CAGED_PATTERNS:
        return quality
    q = str(quality).lower()
    if q.startswith('maj13') or q.startswith('maj9') or q.startswith('maj7'):
        return 'maj7'
    if q.startswith('m7'):
        return 'm7'
    if q.startswith('7'):
        return '7'
    if q.startswith('m'):
        return 'm'
    if q in ('major', 'maj'):
        return 'Major'
    return quality

def _is_caged_shape(shape):
    patterns = CAGED_PATTERNS.get(_caged_quality_key(shape['quality']))
    if not patterns:
        return False
    frets = shape['frets']
    for base in patterns:
        if _matches_caged_pattern(frets, base):
            return True
    return False

def _barre_fret(shape, fret):
    # Barre so conta se alcança a 1a corda (index 5) e nao ha "buracos" (corda solta/muda) no bloco.
    frets = shape['frets']
    if len(frets) < 6:
        return False
    if frets[5] < fret:
        return False

    min_idx = 5
    for i in range(5, -1, -1):
        f = frets[i]
        if f == -1 or f == 0:
            break
        if f < fret:
            break
        min_idx = i

    count_at_fret = sum(1 for i in range(min_idx, 6) if frets[i] == fret)
    return count_at_fret >= 2

def count_fingers(shape):
    fretted = [(i, f) for i, f in enumerate(shape['frets']) if f > 0]
    if not fretted:
        return 0

    by_fret = {}
    for string_idx, fret in fretted:
        by_fret.setdefault(fret, []).append(string_idx)

    fingers = 0
    for fret, strings_at_fret in by_fret.items():
        if _barre_fret(shape, fret):
            fingers += 1
        else:
            fingers += len(strings_at_fret)

    return fingers


def calculate_complexity(shape):
    # Calcula quao "estranho" ou dificil e um acorde. Menor e melhor.
    penalty = 0
    frets = [f for f in shape['frets'] if f > 0] # Apenas casas apertadas
    min_fret = min(frets) if frets else 0

    # 1. Penalidade de Altitude (Tier de Casas)
    if min_fret == 0: penalty -= 10      # Bonus para cordas soltas (Open Chords)
    elif min_fret <= 4: penalty += 0     # Regiao 1-4 (Segura)
    elif min_fret <= 9: penalty += 5     # Regiao 5-9 (Ok)
    elif min_fret > 9: penalty += 25     # Regiao > 10 (Evitar, "Tier Baixo")

    # 2. Penalidade de quantidade de dedos (heuristica simples)
    penalty += count_fingers(shape) * FINGER_PENALTY

    return penalty

# --- GERADOR ---
def generate_chord_shapes(root, quality, max_fret=12):
    root = normalize_root_name(root)
    target_notes = get_chord_notes(root, quality)
    valid_shapes = []
    
    # Otimização de janelas (igual anterior)
    string_maps = []
    for string_idx, open_val in enumerate(TUNING_VALUES):
        possibilities = [-1]
        for fret in range(max_fret + 1):
            if get_note_name(open_val + fret) in target_notes:
                possibilities.append(fret)
        string_maps.append(possibilities)

    windows = [(0, 4)] + [(i, i+4) for i in range(1, max_fret - 3)]

    seen_combinations = set()
    for min_w, max_w in windows:
        window_options = []
        for s_opts in string_maps:
            opts = [f for f in s_opts if f == -1 or f == 0 or (f >= min_w and f <= max_w)]
            window_options.append(opts)
        
        for combo in itertools.product(*window_options):
            active_frets = [f for f in combo if f != -1]
            if not active_frets: continue
            
            # Validações básicas (Tônica presente + Span)
            current_notes = set()
            has_root = False
            for i, f in enumerate(combo):
                if f != -1:
                    n = get_note_name(TUNING_VALUES[i] + f)
                    current_notes.add(n)
                    if n == root: has_root = True
            
            if not has_root: continue
            if len(current_notes) < min(3, len(target_notes)): continue # Pelo menos 3 notas ou o total do acorde

            # Forca tônica no baixo (sem inversões)
            lowest_string_idx = next((i for i, x in enumerate(combo) if x != -1), None)
            if lowest_string_idx is None: continue
            low_note_val = TUNING_VALUES[lowest_string_idx] + combo[lowest_string_idx]
            low_note_name = get_note_name(low_note_val)
            if low_note_name != root: continue
            
            real_frets = [f for f in active_frets if f > 0]
            if real_frets:
                if max(real_frets) - min(real_frets) > 4: continue

            if combo not in seen_combinations:
                avg_pos = sum(real_frets)/len(real_frets) if real_frets else 0
                
                shape_obj = {
                    'frets': combo,
                    'notes': list(current_notes),
                    'position': avg_pos,
                    'root': root,
                    'quality': quality
                }
                # Calcula o Tier aqui mesmo
                shape_obj['complexity'] = calculate_complexity(shape_obj)
                shape_obj['is_caged'] = _is_caged_shape(shape_obj)
                
                valid_shapes.append(shape_obj)
                seen_combinations.add(combo)

    return sorted(valid_shapes, key=lambda x: x['position'])

# --- SOLVER COM PESOS ---
def _is_all_open(shape):
    """True se o shape usa apenas cordas soltas (e/ou mudas), sem notas presas."""
    frets = shape['frets']
    return any(f == 0 for f in frets) and all(f in (0, -1) for f in frets)

def _fretted_signature(shape):
    """Left-hand signature: only string+fret with pressed notes."""
    return tuple((i, f) for i, f in enumerate(shape['frets']) if f > 0)

def _caged_weight(complexity_weight):
    if complexity_weight <= 0:
        return 0.0
    return min(1.0, complexity_weight / 10.0)

def find_best_path(progression_list, complexity_weight=1.0):
    """
    complexity_weight: 
       0.0 = Matemático Puro (Shortest Path apenas por distância)
       1.0 = Balanceado
       5.0 = Tradicional (Evita shapes estranhos a todo custo)
    """
    
    # 1. Gerar
    timeline = []
    for root, quality in progression_list:
        candidates = generate_chord_shapes(root, quality)
        # Em modos não-matemáticos, evita shapes só com cordas soltas.
        if complexity_weight > 0:
            candidates = [s for s in candidates if not _is_all_open(s)]
        if not candidates: return []
        timeline.append(candidates)
    
    # 2. Viterbi Ponderado
    current_paths = []
    caged_weight = _caged_weight(complexity_weight)
    
    # Inicialização
    for shape in timeline[0]:
        # Custo inicial = Posição + Complexidade do primeiro acorde
        caged_bias = -CAGED_BONUS * caged_weight if shape.get('is_caged') else 0
        cost = (shape['position'] * 0.2) + (shape['complexity'] * complexity_weight) + caged_bias
        current_paths.append((cost, [shape]))
        
    # Loop
    for t in range(1, len(timeline)):
        next_candidates = timeline[t]
        new_paths = []
        
        for next_shape in next_candidates:
            best_cost = float('inf')
            best_history = []
            
            for prev_cost, prev_history in current_paths:
                prev_shape = prev_history[-1]
                
                # Custo de Distância (Geometria)
                dist = abs(next_shape['position'] - prev_shape['position'])
                jump_penalty = 10 if dist > 4 else 0

                # Penaliza troca so de cordas (mesma mao esquerda, acorde diferente)
                same_fretted = _fretted_signature(next_shape) == _fretted_signature(prev_shape)
                chord_changed = (next_shape['root'], next_shape['quality']) != (prev_shape['root'], prev_shape['quality'])
                string_only_penalty = 0
                if complexity_weight > 0 and same_fretted and chord_changed:
                    string_only_penalty = 10 * complexity_weight

                
                # Custo de Complexidade (Ergonomia/Ortodoxia)
                # Se o acorde é "estranho" (tier baixo), aumenta o custo
                orthodoxy_cost = next_shape['complexity'] * complexity_weight
                caged_bias = -CAGED_BONUS * caged_weight if next_shape.get('is_caged') else 0

                # Custo Total da Transição
                total_transition = dist + jump_penalty + orthodoxy_cost + string_only_penalty + caged_bias
                
                if (prev_cost + total_transition) < best_cost:
                    best_cost = prev_cost + total_transition
                    best_history = prev_history + [next_shape]
            
            new_paths.append((best_cost, best_history))
        
        current_paths = new_paths

    best_final_path = min(current_paths, key=lambda x: x[0])
    return best_final_path[1]
