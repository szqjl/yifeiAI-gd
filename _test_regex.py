import re

text = open(r'C:\yifeGDBOT\src\game_logic\hand_combiner.py', encoding='utf-8').read()
pattern = r'(^def combine_handcards\(self, handcards[^\n]*\n(?:^ {8,}[^\n]*\n?|^\s*\n)*)'
match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
if match:
    matched = text[match.start():match.end()]
    after = text[match.end():match.end()+80]
    print(f'MATCH OK: len={len(matched)} chars')
    print(f'STARTS: {repr(matched[:60])}')
    print(f'ENDS:   {repr(matched[-60:])}')
    print(f'AFTER:  {repr(after)}')
else:
    print('NO MATCH')