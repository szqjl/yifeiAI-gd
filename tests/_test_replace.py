import re

text = open(r'C:\yifeGDBOT\src\game_logic\hand_combiner.py', encoding='utf-8').read()
pattern = r'(^def combine_handcards\(self, handcards[^\n]*\n(?:^ {8,}[^\n]*\n?|^\s*\n)*)'

# Simulate the lalala replacement (trimmed version)
lalala_code = r'''    def combine_handcards(self, handcards, rank, card_val):
        cards = {}
        cards["Single"] = []
        cards["Pair"] = []
        cards["Trips"] = []
        cards["Bomb"] = []
        bomb_info = {}
        
        handcards = sorted(handcards, key=lambda item: card_val[item[1]])
        start = 0
        for i in range(1, len(handcards) + 1):
            if i == len(handcards) or handcards[i][-1] != handcards[i - 1][-1]:
                if (i - start == 1):
                    cards["Single"].append(handcards[i - 1])
                elif (i - start == 2):
                    cards["Pair"].append(handcards[start:i])
                elif (i - start) == 3:
                    cards["Trips"].append(handcards[start:i])
                else:
                    cards["Bomb"].append(handcards[start:i])
                    bomb_info[handcards[start][-1]] = i - start
                start = i

        return cards, bomb_info'''

match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
replacement = lalala_code.strip()
new_text = text[:match.start()] + '\n' + replacement + '\n' + text[match.end():]

# Write to temp file
tmp = r'C:\yifeGDBOT\src\game_logic\hand_combiner_patched.py'
open(tmp, 'w', encoding='utf-8').write(new_text)

# Check syntax
try:
    compile(open(tmp, encoding='utf-8').read(), tmp, 'exec')
    print('SYNTAX: OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')

# Show context around the replacement boundary
idx = new_text.find(replacement)
before = max(0, idx-100)
after_idx = min(len(new_text), idx+len(replacement)+100)
print(f'\nBEFORE replacement: {repr(new_text[before:idx][-80:])}')
print(f'REPLACEMENT: {repr(new_text[idx:idx+80])}')
print(f'AFTER replacement:  {repr(new_text[idx+len(replacement):after_idx][:80])}')